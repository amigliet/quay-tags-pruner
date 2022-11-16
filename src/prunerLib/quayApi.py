import requests
import os
import copy
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# Disable SSL Warnings
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# This exception is raise when the api call "https://{quay_host}/api/v1/superuser/organizations/" return the error
# "status": 403 "error_message": "Unauthorized", "error_type": "insufficient_scope"
# It means that the QUAY_TOKEN used hasn't the superuser privileges to call this api
class ErrorAPIResponse403InsufficientScope(Exception):
    """Base class for other exceptions"""
    pass


def get_orgs_json(logger, quay_host, app_token):
    base_url = f"https://{quay_host}/api/v1/superuser/organizations/"
    get_headers = {'accept': 'application/json', 'Authorization': 'Bearer '+ app_token }
    try:
        logger.debug(f"Invoke API Request Type: GET URL:{base_url} with the following headers: "
                     "{'accept': 'application/json', 'Authorization': 'Bearer <QUAY_TOKEN_OBFUSCATED> }")
        response = requests.get(
            base_url,
            headers=get_headers,
            timeout=5.0,
            verify=False
        )
        logger.debug(f"API Response: {response.json()}")

        if response.status_code == 403 and response.json()["error_message"] == "Unauthorized" and \
           response.json()["error_type"] == "insufficient_scope":
            raise ErrorAPIResponse403InsufficientScope
        elif response.status_code != 200:
            logger.error(f"Error Quay API request to URL {base_url} has the status code {response.status_code}. The expected status code is 200.\n"
                             f"API response reason: {response.reason}\n"
                             f"API response text: {response.text}")
            os._exit(1)

    except requests.ConnectionError as err:
        logger.exception(f"Connection error: {err}")
    else:
        return response.json()

def get_repo_list_json(logger, quay_host, app_token, quay_org):
    base_url = f"https://{quay_host}/api/v1/repository?namespace={quay_org}"
    get_headers = {'accept': 'application/json', 'Authorization': 'Bearer '+ app_token }
    try:
        logger.debug(f"Invoke API Request Type: GET URL:{base_url} with the following headers: "
                     "{'accept': 'application/json', 'Authorization': 'Bearer <QUAY_TOKEN_OBFUSCATED> }")
        response = requests.get(
            base_url,
            headers=get_headers,
            timeout=5.0,
            verify=False
        )
        logger.debug(f"API Response: {response.json()}")

        if response.status_code != 200:
            logger.error(f"Error Quay API request to URL {base_url} has the status code {response.status_code}. The expected status code is 200.\n"
                             f"API response reason: {response.reason}\n"
                             f"API response text: {response.text}")
            os._exit(1)
        result = response.json()

        # Manage organization with more than 100 repositories using pagination
        while 'next_page' in response.json().keys():
            next_page = response.json()["next_page"]
            base_url = f"https://{quay_host}/api/v1/repository?namespace={quay_org}&next_page={next_page}"

            logger.debug(f"Invoke API Request Type: GET URL:{base_url} with the following headers: "
                         "{'accept': 'application/json', 'Authorization': 'Bearer <QUAY_TOKEN_OBFUSCATED> }")
            response = requests.get(
                base_url,
                headers=get_headers,
                timeout=5.0,
                verify=False
            )
            logger.debug(f"API Response: {response.json()}")

            if response.status_code != 200:
                logger.error(f"Error Quay API request to URL {base_url} has the status code {response.status_code}. The expected status code is 200.\n"
                                 f"API response reason: {response.reason}\n"
                                 f"API response text: {response.text}")
                os._exit(1)

            result["repositories"].extend(copy.deepcopy(response.json()["repositories"]))

    except requests.ConnectionError as err:
        logger.exception(f"Connection error: {err}")
    else:
        return result


# Get information of a specific repository
def get_repo_json(logger, quay_host, app_token, quay_org, image):
    get_headers = {'accept': 'application/json', 'Authorization': 'Bearer '+ app_token }
    base_url = f"https://{quay_host}/api/v1/repository/{quay_org}/{image}"
    try:
        logger.debug(f"Invoke API Request Type: GET URL:{base_url} with the following headers: "
                     "{'accept': 'application/json', 'Authorization': 'Bearer <QUAY_TOKEN_OBFUSCATED> }")
        response = requests.get(
            base_url,
            headers=get_headers,
            timeout=5.0,
            verify=False
        )
        logger.debug(f"API Response: {response.json()}")

        if response.status_code != 200:
            logger.error(f"Error Quay API request to URL {base_url} has the status code {response.status_code}. The expected status code is 200.\n"
                             f"API response reason: {response.reason}\n"
                             f"API response text: {response.text}")
            os._exit(1)
        result = response.json()
    except requests.ConnectionError as err:
        logger.exception(f"Connection error: {err}")
    else:
        return result


def get_tags_json(logger, quay_host, app_token, quay_org, image):
    page=1
    get_headers = {'accept': 'application/json', 'Authorization': 'Bearer '+ app_token }
    base_url = f"https://{quay_host}/api/v1/repository/{quay_org}/{image}/tag/?onlyActiveTags=True&page={page}"
    try:
        logger.debug(f"Invoke API Request Type: GET URL:{base_url} with the following headers: "
                     "{'accept': 'application/json', 'Authorization': 'Bearer <QUAY_TOKEN_OBFUSCATED> }")
        response = requests.get(
            base_url,
            headers=get_headers,
            timeout=5.0,
            verify=False
        )
        logger.debug(f"API Response: {response.json()}")

        if response.status_code != 200:
            logger.error(f"Error Quay API request to URL {base_url} has the status code {response.status_code}. The expected status code is 200.\n"
                             f"API response reason: {response.reason}\n"
                             f"API response text: {response.text}")
            os._exit(1)
        result = response.json()

        # Manage repository with more than 50 tags using pagination
        while response.json()["has_additional"]:
            page += 1
            base_url = f"https://{quay_host}/api/v1/repository/{quay_org}/{image}/tag/?onlyActiveTags=True&page={page}"

            logger.debug(f"Invoke API Request Type: GET URL:{base_url} with the following headers: "
                         "{'accept': 'application/json', 'Authorization': 'Bearer <QUAY_TOKEN_OBFUSCATED> }")
            response = requests.get(
                base_url,
                headers=get_headers,
                timeout=5.0,
                verify=False
            )
            logger.debug(f"API Response: {response.json()}")

            if response.status_code != 200:
                logger.error(f"Error Quay API request to URL {base_url} has the status code {response.status_code}. The expected status code is 200.\n"
                             f"API response reason: {response.reason}\n"
                             f"API response text: {response.text}")
                os._exit(1)
            result["tags"].extend(copy.deepcopy(response.json()["tags"]))

    except requests.ConnectionError as err:
        logger.exception(f"Connection error: {err}")
    else:
        return result


# This function returns an empty list if there aren't errors during tag deletion API Request
# Otherwise it returns a list of strings containing a human-readable message describing the API Response errors
def delete_tags(logger, quay_host, app_token, quay_org, image, tags):
    delete_tag_error_list = []

    base_url = f"https://{quay_host}/api/v1/repository/{quay_org}/{image}/tag"
    get_headers = {'accept': 'application/json', 'Authorization': 'Bearer '+ app_token }
    for tag in tags:
        logger.debug(f"Invoke API Request Type: DELETE URL:{base_url} tag {tag['name']} with the following headers: "
                     "{'accept': 'application/json', 'Authorization': 'Bearer <QUAY_TOKEN_OBFUSCATED> }")
        response = requests.delete(
            f"{base_url}/{tag['name']}",
            headers=get_headers,
            timeout=5.0,
            verify=False
        )
        logger.debug(f"API Response {vars(response)}")

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            if response.status_code == 400:
                logger.info(
                    f"{quay_org}/{image}:{tag['name']} has already been deleted"
                )
            else:
                logger.error(f"Error Quay API request to URL {base_url} has the status code {response.status_code}.\n"
                             f"The expected status code is 200. API response reason: {response.reason}\n"
                             f"API response text: {response.text}")
                delete_tag_error_list.append(
                    f"Error occurred deleting tags {tag['name']} of {quay_org}/{image} Status code API response: "
                    f"{response.status_code} API response reason: {response.reason} API response text: {response.text}")

        else:
            logger.info(f"{quay_org}/{image}:{tag['name']} deleted")

    return delete_tag_error_list
