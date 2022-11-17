import re
import os


def check_environment_variables(logger):
    logger.debug("Execute function check_environment_variables")
    for env_variable in ["DEBUG", "DRY_RUN", "QUAY_URL", "QUAY_APP_TOKEN"]:
        if env_variable not in os.environ:
            logger.error(f"Terminating the application with an error: "
                         f"The required environment variable {env_variable} is not defined"
                         )
            exit(1)

    debug_env_value = os.getenv("DEBUG")
    if not isinstance( debug_env_value, str) and debug_env_value.lower() not in ["true", "false"]:
        logger.error(f"Terminating the application with an error in the configuration file: "
                     f"The value '{debug_env_value}' of environment variables DEBUG is not a valid."
                     f"Allowed values: 'true','True','False or 'false'"
                     )
        exit(1)

    dry_run_env_value = os.getenv("DRY_RUN")
    if not isinstance( dry_run_env_value, bool)  and dry_run_env_value.lower() not in ["true", "false"]:
        logger.error(f"Terminating the application with an error in the configuration file: "
                     f"The value '{dry_run_env_value}' of environment variables DRY_RUN is not a valid."
                     f"Allowed values: 'true','True','False or 'false'"
                     )
        exit(1)
    logger.debug("Function check_environment_variables completed with success")

    quay_api_timeout = os.getenv("QUAY_API_TIMEOUT")
    if quay_api_timeout is not None and not quay_api_timeout.replace('.','',1).isdigit():
        logger.error(f"Terminating the application with an error in the environment variables: "
                     f"The value '{quay_api_timeout}' of environment variables QUAY_API_TIMEOUT is not a valid float"
                     f"number. (example valid value 60.0)'"
                     )
        exit(1)
    logger.debug("Function check_environment_variables completed with success")


def check_configuration_file(logger, conf_yaml):
    logger.debug("Execute function checkConfigurationFilee")

    verify_existence_key_rules(logger, conf_yaml)
    verify_existence_key_default_rule(logger, conf_yaml)
    verify_value_of_rules_is_a_list(logger, conf_yaml)
    verify_value_of_default_rule_is_a_dictionary(logger, conf_yaml)
    verify_existence_key_enabled_in_default_rule(logger, conf_yaml)
    verify_value_of_key_enabled_in_default_rule(logger, conf_yaml)
    verify_existence_key_exclude_organizations_regex_in_default_rule(logger, conf_yaml)
    verify_value_of_key_exclude_organizations_regex_in_default_rule(logger, conf_yaml)
    verify_existence_key_parameters_in_default_rule(logger, conf_yaml)

    for rule in conf_yaml["rules"]:
        verify_rule(logger, rule)

    for parameter in conf_yaml["default_rule"]["parameters"]:
        verify_parameter(logger,parameter)

    logger.debug("Function check_configuration_file completed with success")


def verify_existence_key_rules(logger, conf_yaml):
    if 'rules' not in conf_yaml.keys():
        logger.error("Terminating the application with an error in the configuration file: "
                     "The key 'rules' is missing in the configuration file config.yaml"
                     )
        exit(1)


def verify_existence_key_default_rule(logger, conf_yaml):
    if 'default_rule' not in conf_yaml.keys():
        logger.error("Terminating the application with an error in the configuration file: "
                     "The key 'default_rule' is missing in the configuration file config.yaml"
                     )
        exit(1)


def verify_value_of_rules_is_a_list(logger, conf_yaml):
    if not isinstance(conf_yaml["rules"], list):
        logger.error("Terminating the application with an error in the configuration file: "
                     "The value of key 'rules' is not a list"
                     )
        exit(1)


def verify_value_of_default_rule_is_a_dictionary(logger, conf_yaml):
    if not isinstance(conf_yaml["default_rule"], dict):
        logger.error("Terminating the application with an error in the configuration file: "
                     "The value of key 'default_rule' is not a dictionary"
                     )
        exit(1)


def verify_existence_key_enabled_in_default_rule(logger, conf_yaml):
    if 'enabled' not in conf_yaml["default_rule"].keys():
        logger.error("Terminating the application with an error in the configuration file: "
                     "The key 'enabled' is not defined inside 'default_rule' dictionary"
                     )
        exit(1)


def verify_value_of_key_enabled_in_default_rule(logger, conf_yaml):
    if not isinstance(conf_yaml["default_rule"]["enabled"], bool):
        logger.error("Terminating the application with an error in the configuration file: "
                     "The value of key 'enabled' in default_rule section it not a boolean. Allowed values: "
                     "True or False"
                     )
        exit(1)


def verify_existence_key_parameters_in_default_rule(logger, conf_yaml):
    if 'parameters' not in conf_yaml["default_rule"].keys():
        logger.error("Terminating the application with an error in the configuration file: "
                     "The key 'parameters' is not defined inside 'default_rule' dictionary"
                     )
        exit(1)

def verify_value_of_key_exclude_organizations_regex_in_default_rule(logger, conf_yaml):
    if not isinstance(conf_yaml["default_rule"]["exclude_organizations_regex"], str):
        logger.error("Terminating the application with an error in the configuration file: "
                     "The value of key 'exclude_organizations_regex' in default_rule section it not a string. "
                     )
        exit(1)

    # check that exclude_organizations_regex is a valid regular expression
    try:
        re.compile(conf_yaml["default_rule"]["exclude_organizations_regex"])
        exclude_organizations_regex_is_valid = True
    except re.error:
        exclude_organizations_regex_is_valid = False
    if not exclude_organizations_regex_is_valid:
        logger.error(f"Terminating the application with an error in the configuration file: "
                     f"The parameter exclude_organizations_regex is not valid, the value of the key "
                     f"exclude_organizations_regex' is not a regular expression"
                     )
        exit(1)


def verify_existence_key_exclude_organizations_regex_in_default_rule(logger, conf_yaml):
    if 'exclude_organizations_regex' not in conf_yaml["default_rule"].keys():
        logger.error("Terminating the application with an error in the configuration file: "
                     "The key 'exclude_organizations_regex' is not defined inside 'default_rule' dictionary"
                     )
        exit(1)


def verify_rule(logger, rule):
    if 'organization_list' not in rule.keys():
        logger.error(f"Terminating the application with an error in the configuration file: "
                     f"The rule key {rule} is not valid, the key 'organization_list' is missing"
                     )
        exit(1)

    if 'parameters' not in rule.keys():
        logger.error(f"Terminating the application with an error in the configuration file: "
                     f"The rule key {rule} is not valid, the key 'parameters' is missing"
                     )
        exit(1)

    if not isinstance(rule["organization_list"], list):
        logger.error(f"Terminating the application with an error in the configuration file: "
                     f"The rule key {rule} is not valid, the value of key 'organization_list' is not a list"
                     )
        exit(1)

    for organization in rule["organization_list"]:
        if not isinstance(organization, str) and not isinstance(organization, int):
            logger.error(f"Terminating the application with an error in the configuration file: "
                         f"The rule key {rule} is not valid, the organization_list list contains the value "
                         f"{organization} that is not a string or a integer"
                         )
            exit(1)

    if not isinstance(rule["parameters"], list):
        logger.error(f"Terminating the application with an error in the configuration file: "
                     f"The rule {rule} is not valid, the value of key 'parameters' is not a list"
                     )
        exit(1)

    for parameter in rule["parameters"]:
        verify_parameter(logger, parameter)


def verify_parameter(logger,parameter):
    if not isinstance(parameter, dict):
        logger.error(f"Terminating the application with an error in the configuration file: "
                     f"The parameter {parameter} is not valid, it is not a dictionary"
                     )
        exit(1)

    if 'tag_filter' not in parameter.keys():
        logger.error(f"Terminating the application with an error in the configuration file: "
                     f"The parameter {parameter} is not valid, the key 'tag_filter' is missing"
                     )
        exit(1)

    if 'keep_n_tags' not in parameter.keys() and 'keep_tags_younger_than' not in parameter.keys():
        logger.error(f"Terminating the application with an error in the configuration file: "
                     f"The parameter {parameter} is not valid, both the keys 'keep_n_tags' and 'keep_tags_younger_than' "
                     f"are missing, at least one of these two option is required"
                     )
        exit(1)

    not_valid_parameter_keys=list(parameter.keys())
    if "tag_filter" in not_valid_parameter_keys:
        not_valid_parameter_keys.remove("tag_filter")
    if "keep_n_tags" in not_valid_parameter_keys:
        not_valid_parameter_keys.remove("keep_n_tags")
    if "keep_tags_younger_than" in not_valid_parameter_keys:
        not_valid_parameter_keys.remove("keep_tags_younger_than")

    if len(not_valid_parameter_keys) > 0:
        logger.error(f"Terminating the application with an error in the configuration file: "
                     f"The parameter {parameter} is not valid, the following keys are not recognized: "
                     f"{not_valid_parameter_keys}"
                     )
        exit(1)

    if not isinstance(parameter["tag_filter"], str):
        logger.error(f"Terminating the application with an error in the configuration file: "
                     f"The parameter {parameter} is not valid, the value of the key 'tag_filter' is not a string"
                     )
        exit(1)

    # check that tag_filter is a regular expression
    try:
        re.compile(parameter["tag_filter"])
        tag_filter_is_valid = True
    except re.error:
        tag_filter_is_valid = False
    if not tag_filter_is_valid:
        logger.error(f"Terminating the application with an error in the configuration file: "
                     f"The parameter {parameter} is not valid, the value of the key 'tag_filter' is not a regular "
                     f"expression"
                     )
        exit(1)

    if 'keep_n_tags' in parameter.keys() \
            and \
            not (isinstance(parameter["keep_n_tags"], str) and parameter["keep_n_tags"].isdigit()):
        logger.error(f"Terminating the application with an error in the configuration file: "
                     f"The parameter {parameter} is not valid, the value of the key 'keep_n_tags' is not a string "
                     f"representing a integer"
                     )
        exit(1)

    if 'keep_tags_younger_than' in parameter.keys() \
            and \
            not (isinstance(parameter["keep_tags_younger_than"], str) and parameter["keep_tags_younger_than"].isdigit()):
        logger.error(f"Terminating the application with an error in the configuration file: "
                     f"The parameter {parameter} is not valid, the value of the key 'keep_tags_younger_than' is not a "
                     f"string representing an integer"
                     )
        exit(1)
