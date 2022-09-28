import copy
import json
import logging
import os
import re
import yaml
import time
from prunerLib import checkConfiguration
from prunerLib import quayApi


def setup_logger():
    logger_initialization = logging.getLogger('pruner')
    logger_initialization.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s')
    ch.setFormatter(formatter)

    logger_initialization.addHandler(ch)
    return logger_initialization


def get_orgs_list(quay_host, app_token):
    org_list_json = quayApi.get_orgs_json(logger, quay_host, app_token)

    org_list = []
    for o in org_list_json["organizations"]:
        org_list.append(o["name"])

    return org_list


# Get the parameter state of a repository ( used to extract the state and skip repo with state MIRROR or READ_ONLY)
def get_repo_state_parameter(quay_host, app_token, quay_org, image):
    api_response=quayApi.get_repo_json(logger, quay_host, app_token, quay_org, image)
    return api_response["state"]




# This function can be used to print tags' list of dictionary in logs printing only important tags' values
# This function accepts as input a list of dictionary and return as result the same list of dict removing the dict keys
# different from [name,start_ts,last_modified]
def prettify_tag_list_of_dict(input_list):
    result = []
    for tag in input_list:
        result.append({
                     "name" : tag["name"],
                     "last_modified": tag["last_modified"],
                     "start_ts": tag["start_ts"]
                      }
        )
    return result


# This function selects and returns the tags that need to be removed based on the values defined in the variable
# parameter
def select_tags_to_remove(organization,repository,tags, parameter, current_ts):
    logger.debug(
        f"Invoke function select_tags_to_remove with the following parameters:\n"
        f"organization {organization}\n"
        f"repository {repository}\n"
        f"tags {tags}\n"
        f"parameter {parameter}\n"
        f"current_ts {current_ts}\n"
    )

    # The dictionary parameter must be contains at least one of the two keys keep_tags_younger_than and keep_n_tags
    if 'keep_n_tags' not in parameter.keys() and 'keep_tags_younger_than' not in parameter.keys():
        logger.error(
            f"Error: The dictionary parameter of repository {repository} of the organization {organization} must "
            f"contain at least one of the following parameters: keep_n_tags keep_tags_younger_than")
        os._exit(1)

    # Filter tags based on the regular expression defined in tag_filter
    pattern=parameter["tag_filter"]
    matches = []
    for tag in tags["tags"]:
        match = re.search(pattern, tag["name"])
        if match:
            matches.append(tag)
    matches_len = len(matches)
    logger.debug(f"The following tags { [tag['name'] for tag in matches] } have been matched by the regular expression {pattern} ")

    # If keep_n_tags is defined in parameter, filter the tags that needs to be deleted based on this condition and store
    # them in tag_deleted_by_keep_tag_number
    if "keep_n_tags" in parameter.keys():
        keep_tag_number=int(parameter["keep_n_tags"])
        if matches_len > keep_tag_number:
            end_index = matches_len - keep_tag_number
            sorted_matches = sorted(matches, key=lambda t: t["start_ts"])
            tag_deleted_by_keep_tag_number = sorted_matches[0:end_index]
        else:
            tag_deleted_by_keep_tag_number = []
        logger.debug (f"The tags of the organization '{organization}' and repository '{repository}' that can be "
                      f"deleted based on parameter 'keep_n_tags: '{keep_tag_number}' are: "
                      f"{json.dumps(prettify_tag_list_of_dict(tag_deleted_by_keep_tag_number), indent=4)} ")

    # If keep_tags_younger_than is defined in parameter, filter the tags that needs to be deleted based on this
    # condition and store them in tag_deleted_by_keep_tags_younger_than
    if "keep_tags_younger_than" in parameter.keys():
        keep_tags_younger_than = int(parameter["keep_tags_younger_than"])
        # the unit of measure of keep_tags_younger_than is days,keep_tags_younger_than_seconds convert it in seconds
        keep_tags_younger_than_seconds=keep_tags_younger_than*24*3600
        # Select tags if the different between current timestamp and the tag start_ts value is greater than
        # keep_tags_younger_than_seconds
        tag_deleted_by_keep_tags_younger_than=[tag for tag in matches
                                                   if (current_ts - tag["start_ts"] ) >  keep_tags_younger_than_seconds
                                               ]
        logger.debug(f"The tags of the organization '{organization}' and repository '{repository}' that can be deleted "
                     f"based on parameter 'keep_tags_younger_than: '{keep_tags_younger_than}' are: "
                     f"{json.dumps(prettify_tag_list_of_dict(tag_deleted_by_keep_tags_younger_than), indent=4)}")

    result=[]
    # If keep_n_tags and keep_tags_younger_than parameters are both defined, the function return the intersection of
    # both list tag_deleted_by_keep_tag_number tag_deleted_by_keep_tags_younger_than
    # A tag will be selected to be deleted only if tag is present in tag_deleted_by_keep_tag_number and
    # tag_deleted_by_keep_tags_younger_than
    if 'keep_n_tags' in parameter.keys() and 'keep_tags_younger_than' in parameter.keys():
        for tag1 in tag_deleted_by_keep_tag_number:
            if any(tag2['name'] == tag1['name'] for tag2 in tag_deleted_by_keep_tags_younger_than):
                result.append(copy.deepcopy(tag1))

    # If keep_n_tags parameter is defined and keep_tags_younger_than parameter is not defined, the function returns the
    # tag deleted based on the condition keep_n_tags
    elif 'keep_n_tags' in parameter.keys() and 'keep_tags_younger_than' not in parameter.keys():
        result=tag_deleted_by_keep_tag_number
    # If tag_deleted_by_keep_tags_younger_than parameter is defined and keep_n_tags parameter is not defined, the
    # function returns the tag deleted based on the condition tag_deleted_by_keep_tags_younger_than
    elif 'keep_tags_younger_than' in parameter.keys() and 'keep_n_tags' not in parameter.keys():
        result=tag_deleted_by_keep_tags_younger_than

    logger.debug(f"The tags of the organization '{organization}' and repository '{repository}' that can be deleted "
                f"based on all the parameters '{parameter}' are: "
                f"{json.dumps( prettify_tag_list_of_dict(result),indent=4 )}")
    return result


# This function returns an empty list if there aren't errors during tag deletion API Request
# Otherwise it returns a list of strings containing a human-readable message describing the API Response errors
def apply_pruner_rule(
        quay_host, app_token, organization,
        parameters, debug, dry_run):
    logger.debug(
        f"Invoke function apply_pruner_rule with the following parameters:\n"
        f"quay_host {quay_host}\n"
        f"app_token {app_token}\n"
        f"organization {organization}\n"
        f"parameters {parameters}\n"
        f"debug {debug}\n"
        f"dry_run {dry_run}"
    )
    delete_tag_error_list = []

    repos = quayApi.get_repo_list_json(logger, quay_host, app_token, organization)
    if repos is None:
       return

    logger.debug(
        f"{organization}'s repositories: {json.dumps(repos, indent=4)}"
    )

    for image in repos["repositories"]:

        repository_state = get_repo_state_parameter(quay_host, app_token, organization, image["name"])
        if repository_state in ["MIRROR", "READ_ONLY"]:
            image_name=image["name"]
            logger.warning(f"The repository ' {organization} / {image_name} has been skipped because its state is "
                           f"{repository_state}")
            continue

        for param in parameters:
            logger.info(f"Apply filter: {param['tag_filter']}")
            image_tags = quayApi.get_tags_json(logger,quay_host, app_token, organization, image["name"])
            if image_tags is None:
                continue

            current_ts=int(time.time())
            bad_tags = select_tags_to_remove(organization,image["name"],image_tags, param, current_ts)
            if bad_tags is None:
                logger.info(
                    f"No tags to delete found for image {image['name']} "
                    f"with pattern {param['tag_filter']}"
                )
                continue

            if dry_run:
                for tag in prettify_tag_list_of_dict(bad_tags):
                    logger.info( f"DRY-RUN Candidate tags for deletion "
                                 f"for image {organization} / {image['name']}:{tag['name']}"
                                 f"\t\tlast_modified: {tag['last_modified']} \tstart_ts: {tag['start_ts']}"
                                 )
            else:
                current_repository_delete_tags_result = quayApi.delete_tags(logger, quay_host, app_token, organization, image["name"], bad_tags)
                if current_repository_delete_tags_result != []:
                    delete_tag_error_list.extend(current_repository_delete_tags_result)

    return delete_tag_error_list

if __name__ == "__main__":
    logger = setup_logger()

    checkConfiguration.check_environment_variables(logger)

    debug = True if os.getenv('DEBUG', 'False').upper() == 'TRUE' else False
    dryRun = True if os.getenv('DRY_RUN', 'False').upper() == 'TRUE' else False
    quayUrl = os.getenv('QUAY_URL')
    oauthToken = os.getenv('QUAY_APP_TOKEN')

    logger.info(f"DEBUG {debug}, DRY_RUN {dryRun}, QUAY_URL {quayUrl}")
    if debug:
        logger.debug(f"Quay App Token: {oauthToken}")

    configFile = "/opt/conf/config.yaml"
    try:
        with open(configFile, "r") as fp:
            conf_yaml = yaml.safe_load(fp.read())
        if debug:
            logger.debug(f"Loaded file config.yaml:\n{yaml.dump(conf_yaml)}")
        checkConfiguration.check_configuration_file(logger, conf_yaml)

    except IOError as err:
        logger.exception(f"Error reading file {configFile}: {err}")
        os._exit(1)

    # Define a list of potential errors occurred during the Quay delete tags API requests to show them at the end
    # of the application execution
    tags_delete_errors_list=[]

    # Evaluate rules for specific organization lists
    for rule in conf_yaml["rules"]:
        params = rule["parameters"]

        for org in rule["organization_list"]:
            tags_delete_errors_list_during_apply_pruner_rule=apply_pruner_rule(quayUrl, oauthToken, org, params, debug, dryRun)
            if tags_delete_errors_list_during_apply_pruner_rule != []:
                tags_delete_errors_list.extend(tags_delete_errors_list_during_apply_pruner_rule)

    # Evaluate default rule
    if conf_yaml["default_rule"]["enabled"]:

        try:
            org_list = get_orgs_list(quayUrl, oauthToken)
        except quayApi.ErrorAPIResponse403InsufficientScope:
            logger.error(f"The token provided by 'QUAY_TOKEN' environment variable hasn't superadmin privileges and "
                         f"the call to the API 'https://{quayUrl}/api/v1/user/authorizations' has failed with the "
                         f"error 'Insufficient scope' status code 403. If you want use an access token without "
                         f"superadmin privileges disable the default_rule in the configuration file. If you want enable"
                         f"the default rule, provide a token with superadmin privileges using the environment variable "
                         f"'QUAY_TOKEN'")
            os._exit(1)

        if debug:
            logger.debug(f"Organizations complete list: {org_list}")

        org_exclude_list = []
        for r in conf_yaml["rules"]:
            for o in r["organization_list"]:
                org_exclude_list.append(o)
        if debug:
            logger.debug(f"Organizations exclude list: {org_exclude_list}")

        org_default_list = list(set(org_list).difference(set(org_exclude_list)))
        logger.info(f"Organizations pruned by default_rule: {org_default_list}")

        default_params = conf_yaml["default_rule"]["parameters"]

        for org in org_default_list:
            tags_delete_errors_list_during_apply_pruner_rule=apply_pruner_rule(quayUrl, oauthToken, org, default_params, debug, dryRun)
            if tags_delete_errors_list_during_apply_pruner_rule != []:
                tags_delete_errors_list.extend(tags_delete_errors_list_during_apply_pruner_rule)

    if tags_delete_errors_list == []:
        logger.info("Application has terminated successfully")
    else:
        # convert list of string to multi-line string
        tags_delete_errors_list_multiline_str = "\n".join(tags_delete_errors_list)
        logger.error(f"Application has terminated with the following errors on tag deletion API Requests:\n"
                     f"{tags_delete_errors_list_multiline_str}")
        os._exit(1)