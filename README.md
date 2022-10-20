# quay-tags-pruner

Simple application to prune tags of images placed on a Red Hat Quay registry.

## Overview

This application:
  - Searches the given list of organizations for images
  - Scans the images for the desired tag patterns
  - For each tag pattern it deletes all the tags based on rules defined in the application configuration file named
    "config.yaml" (i.e. delete all tags except for the N most recent). More details about the rules are documented in
    the paragraph"Configuration file description" of this document

This application accepts the following inputs:
* **Environment variables** (specified in the CronJob "quay-tags-pruner" when this application run on OpenShift):
    - **QUAY_URL** This is the FQDN of the quay registry subject of the image tags pruning
      (i.e. instance-quay-quay-registry.apps.ocp.example.com )
    - **DRY_RUN** This boolean variable accepts only two values "True" or "False". If the value
      of this variable is "True", it enables the DRY_RUN mode, any changes will be executed by the
      application but the application only show to the standard output the task that it would execute
    - **DEBUG** This boolean variable accepts only two values "True" or "False". If the value
      of this variable is "True", it increases the verbosity of the logging messages


* **Environment variables** (specified in the secret "quay-tags-pruner-token" when this application run on OpenShift):
    - **QUAY_APP_TOKEN** This is an OAuth Token configured on the Quay Registry. It is used by
      the application to search organizations, repositories and tags and to prune tags


* **Configuration file** (specified in the config map "quay-tags-pruner-config" when this application run on OpenShift):
    - **config.yaml** This YAML file contains the definition of the rule used by the application to prune the image
      tags.

**Important note: This application doesn't prune tags of repositories with state 'MIRROR' (repositories with mirror
settings enabled) o 'READ_ONLY'. When this application identify a repository with one of these states, it prints a 
warning messages, skip the repository and continue its execution. On both cases the API call to delete tags from the 
repositories fails.**

## Configuration file description

The following textbox contains an example of the configuration file config.yaml.
The following part of this paragraph describes this configuration file.

```
rules:
  - organization_list:
      - org1
      - org2
    parameters:
    - tag_filter: "."
      keep_n_tags: "5"
      keep_tags_younger_than: "60"
  - organization_list:
      - org3
    parameters:
    - tag_filter: ".*prod.*"
      keep_n_tags: "15"
      keep_tags_younger_than: "60"
    - tag_filter: ".*test.*"
      keep_n_tags: "20"
      keep_tags_younger_than: "120"
default_rule:
  enabled: True
  exclude_organizations_regex: "^org4$|^org5$"
  parameters:
    - tag_filter: "."
      keep_n_tags: "10"
      keep_tags_younger_than: "90"
```

### Rules description
The "config.yaml" file is a dictionary with two keys:

* **rules** (specified in the secret "quay-tags-pruner-token" when this application run on OpenShift):
  The pruning parameters of these rules are applied only to specific organizations defined in the parameter
  organization_list of each rule. Different pruning parameters for different set of organizations can be specified
  inserting different rules for each set of organizations in the rules section of the configuration file.
* **default rule** (specified in the secret "quay-tags-pruner-token" when this application run on OpenShift): The
  pruning parameters of the default rule is applied (if the default rule is enabled using the parameter "enabled") is
  applied to all the organizations of the Quay registry except to the organization already specified in the
  organization_list parameters of the rules. The default rule can be enabled or disabled modifying the parameter enabled
  that accepts only two values "True" or "False". The default rule can be enabled only if the access token used by the
  application has superadmin privileges (see more details in the paragraph 'Access token configuration').
  The default rule contains also a required parameter named 'exclude_organizations_regex'. If the value of
  'exclude_organizations_regex' is a valid regular expression, the organizations matching this regular expression are
  excluded by the default rule pruning parameter and no tags are deleted on their repositories by this application.
  If 'exclude_organizations_regex' contains an empty string, this parameter doesn't exclude any organization.

### Pruning parameters description

In each rule and in the default rule, a list of pruning parameters must be specified.
If you want to define some pruning parameters for all the tags of all repositories of an organization, you can specify a
single pruning parameter.
If you want to define different pruning parameters to different set of tags of all repositories of an organization, you
have to define a list of pruning parameter(one pruning parameter for each set of tags).


Each pruning parameter is a dictionary composed by tree keys:
* **tag_filter** It is a regular expression string to select a set of tags. If you want to create a tag_filter to select
  all the tags of all repositories of organization defined in organization_list you can use the value "." for the key
  "tag_filter"
* **keep_n_tags** This parameter defines the number of most recent uploaded tags(filtered using the parameter
  tag_filter) to keep in the repositories. All the other tags (filtered using the parameter
  tag_filter) will be deleted by this application
* **keep_tags_younger_than** This parameter uses a unit of measurement the days. This parameter allow to define the
  number of days of the tag creation dates(tags always filtered using the parameter tag_filter) of the oldest tag that
  is keep in quay. All the tags (filtered using the parameter tag_filter) uploaded in quay before the days specified in
  this parameter will be deleted.
  All the tags (filtered using the parameter tag_filter) uploaded in quay after the days specified in
  this parameter will be keep in the Quay registry


The parameter "tag_filter" is **required** in each pruning parameter.

The parameters "keep_n_tags" and "keep_tags_younger_than" are **optional** but at least one of them must be specified in
each pruning parameter. When both "keep_n_tags" and "keep_tags_younger_than" condition are specified, both are verified
before to delete the tags (i.e. Keep the most recent n tags and the tags uploaded after x days and then delete all the
other tags not mathing these conditions)


The following text box contains an example configuration file with different rules and a comment/description of the
pruning parameters of each rule:

```
rules:
  - organization_list:
      - org1
      - org2
    # Keep the most recent 5 tags of each reposities of the organization "org1" and "org2" and delete all the other tags
    # of these repositories of these repositories
    parameters:
    - tag_filter: "."
      keep_n_tags: "5"
  - organization_list:
      - org3
    parameters:
    # Keep the tags uploaded before 120 days ago of each reposities of the organization "org3" and delete all the other
    # tags of these repositories
    - tag_filter: "."
      keep_tags_younger_than: "120"
  - organization_list:
      - org4
    parameters:
    # Keep the tags uploaded before 120 days ago of each reposities of the organization "org4" but also keep at least
    # the most 10 recents tags uploaded and delete all the other tags of these repositories
    - tag_filter: "."
      keep_tags_younger_than: "60"
      keep_n_tags: "10"
  - organization_list:
      - org5
    parameters:
    # Keep the 2 most recent uploaded tags matching the regular expression "v.[0-9]+.[0-9]+.[0-9]+-rc[0-9]+" of all
    # repositories of the organization org5 and delete all the other tags matching this regular expression
    - tag_filter: "v[0-9]+.[0-9]+.[0-9]+-rc[0-9]+"
      keep_n_tags: "2"
    # Keep the 5 most recent uploaded tags matching the regular expression "v.[0-9]+.[0-9]+.[0-9]+-dev[0-9]+" of all
    # repositories of the organization org5 and delete all the other tags matching this regular expression
    - tag_filter: "v[0-9]+.[0-9]+.[0-9]+-dev[0-9]+"
      keep_n_tags: "5"
  - organization_list:
      - org6
    parameters:
    # Keep the tags containing the string "prod" in their name uploaded before 120 days ago of each reposities of the
    # organization "org6" but delete all the other tags containing the string "prod" in their name of these repositories
    - tag_filter: "prod"
      keep_tags_younger_than: "120"
    # Keep the tags containing the string "test" in their name uploaded before 60 days ago of each reposities of the
    # organization "org4" but delete all the other tags containing the string "prod" in their name of these repositories
    # Note: all the tags not containing in their name the string "prod" or "test" will not be touched
    - tag_filter: "test"
      keep_tags_younger_than: "60"
default_rule:
  enabled: False
  exclude_organizations_regex: ""
  parameters:
    - tag_filter: "."
      keep_n_tags: "10"
      keep_tags_younger_than: "90"
```

## Quay configuration requirement to use quay-tags-pruner

This section describes the prerequisite Quay configuration needed to execute quay-tags-pruner application against a Quay registry

### Access token configuration

The Quay OAuth access token specified using the environment variable QUAY_URL is used to authenticate any API call executed
to the Quay registry.
The quay-tags-pruner application can be used with two different set of privileges of the OAuth access token.
The behaviour of the application changes based on the privileges assigned to the access token as described in the following table:

| Application mode | Permission of OAuth Access Token                                                                                       | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
|------------------|------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Superuser        | 1) View all visible repositories<br/><br/>2) Read/Write to any accessible repositories<br/><br/>3) Super User Access   | Using this application mode, the default_rule can be enabled.<br/><br/>The user owner of this OAuth Access Token must have superadmin privileges configured in the Quay registry configuration<br/><br/>The user associated to the OAuth token must have the following permission:<br/>1) "Write" permission on the repositories of the organizations defined in the configuration rule parameter<br/>2) "Write" permission on all the Quay organization if the default_rule is enabled                     |
| Standard user    | 1) View all visible repositories<br/><br/>2) Read/Write to any accessible repositories                                 | Using this application mode the organizations used by pruner must be explicitly defined in the rule parameter of the configuration file and the default_rule can't be enabled<br/><br/>The user owner of this OAuth Access Token doesn't need superadmin privileges configured in the Quay registry<br/><br/><br/>The user associated to the OAuth token must have the following permission:<br/>1) "Write" permission on the repositories of the organizations defined in the configuration rule parameter |

The prerequisites to create a Quay OAuth access token are:
- create a Quay organization
- login with the user that will be associated to the OAuth Access token

The Red Hat documentation [1] describes the procedure to create a Quay OAuth access token, use the permission specified
in the column "Permission of OAuth Access Token" of the previous table when required to select them in the procedure.

### Repository configuration

The user associated to the OAuth Access token need "write" access to all repositories(except the repositories with state
'MIRROR' and 'READ_ONLY') defined in the organization defined in the following list:
1) All the organizations defined in the rules section of the configuration file
2) If the default_rule is enables, All the organization configured on the Quay registry

## Monitoring

The status of the application can be monitored using the prometheus rule defined in the file
helm/pruner/templates/prometheusrule.yaml.
This prometheus rule is firing an alarm named "QuayTagsPrunerJobStatusFailed" when there are failed Job in the
quay-tags-pruner application namespace.


The file helm/pruner/templates/values.yaml contains the following configuration variables related to this prometheus
rule:
```
$ grep prometheusRule helm/pruner/values.yaml 
# A booolean variabile. If it is set to true, the prometheus rule is deployed
prometheusRuleDeploy: true

# The name of the alarm
prometheusRuleAlertName: "QuayTagsPrunerJobStatusFailed"

# Define the severity of the prometheus rule (allowed values: critical, error, warning, info )
prometheusRuleAlertSeverity: "error"
```

In order to ackowledge the error, the kubernetes job resources in error state can be deleted

## Developing
### Create a developing environment on a workstation to run/debug the application without using container

The following command allows to configure the configuration files:

```
sudo mkdir -p /opt/conf/
USER=$(whoami) sudo chown $USER /opt/conf/
ln -s $PWD/helm/pruner/config.yaml /opt/conf/config.yaml
```

The following command executes the application:

```
QUAY_URL="<quay_hostname>" QUAY_APP_TOKEN="<quay_oauth_token>" DEBUG="True" DRY_RUN="True"  python3 src/pruner.py
```

### Run quay-tags-pruner container with podman using the script pruner.py as entrypoint

```
# Verify that the localhost/pruner:latest image has been build as described in the paragraph "Build from Dockerfile"
$ podman images localhost/pruner:latest
REPOSITORY        TAG         IMAGE ID      CREATED      SIZE
localhost/pruner  latest      9357e815a5f8  3 hours ago  298 MB

# Create the podman volume pruner_conf_directory
$ podman volume create pruner_conf_directory

# Create the container
# Note: Replace the strings "<True|False>" "<INSERT_THE_QUAY_APP_TOKEN>" "<INSERT_THE_QUAY_URL>" with the appropriate
# values for your environment
$ podman create --name pruner                                    \
                --user 1001                                      \
                -v pruner_config_directory:/opt/conf             \
                --env DEBUG=<True|False>                         \
                --env DRY_RUN=<True|False>                       \
                --env QUAY_APP_TOKEN=<INSERT_THE_QUAY_APP_TOKEN> \
                --env QUAY_URL=<INSERT_THE_QUAY_URL>             \
                localhost/pruner:latest

# Copy the config.yaml file to the podman volume pruner_conf_directory
$ podman cp --archive helm/pruner/config.yaml pruner:/opt/conf

# Start the container
$ podman start pruner

# Verify the status of the container. The script ends when the pruner.py script ends

$ podman ps -a --filter name=pruner
CONTAINER ID  IMAGE                    COMMAND     CREATED         STATUS                     PORTS       NAMES
01d95edb7b1f  localhost/pruner:latest              54 seconds ago  Exited (0) 39 seconds ago              pruner

# Verify the logs of the container, this logs container the output of the script
$ podman logs pruner
```

### Run quay-tags-pruner container with podman using the shell bash and run manually the script pruner.py

```
# Verify that the localhost/pruner:latest image has been build as described in the paragraph "Build from Dockerfile"
$ podman images localhost/pruner:latest
REPOSITORY        TAG         IMAGE ID      CREATED      SIZE
localhost/pruner  latest      9357e815a5f8  3 hours ago  298 MB

# Create the podman volume pruner_conf_directory
$ podman volume create pruner_conf_directory

# Create the container
# Note: Replace the strings "<True|False>" "<INSERT_THE_QUAY_APP_TOKEN>" "<INSERT_THE_QUAY_URL>" with the appropriate
# values of your environment
$ podman create --name pruner                                    \
              --user 1001                                        \
              -v pruner_config_directory:/opt/conf               \
              --env DEBUG=<True|False>                           \
              --env DRY_RUN=<True|False>                         \
              --env QUAY_APP_TOKEN=<INSERT_THE_QUAY_APP_TOKEN>   \
              --env QUAY_URL=<INSERT_THE_QUAY_URL>               \
              --entrypoint="/bin/bash"                           \
              -ti                                                \
              localhost/pruner:latest

# Copy the config.yaml file to the podman volume pruner_conf_directory
$ podman cp --archive helm/pruner/config.yaml pruner:/opt/conf

# Start the container
$ podman start pruner

# Open a bash session on the container
$ podman exec -ti pruner /bin/bash

# Run the python script /usr/bin/pruner.py using the interpeter /usr/bin/python3.8
$ /usr/bin/python3.8 -u /usr/bin/pruner.py
```

### Clean podman environment after the execution of the quay-tags-pruner container

```
# Stop the container
$ podman stop pruner

# Remove the container
$ podman rm pruner

# Remove the podman volume pruner_conf_directory
$ podman volume rm pruner_conf_directory
```

## Installation
### Build from Dockerfile

Clone this repository and build an image:

```
$ git clone https://github.com/amigliet/quay-tags-pruner.git
$ cd quay-tags-pruner
$ podman build -t pruner .
```

### Deploy on OpenShift
This section describe how to deploy this app as a CronJob on OpenShift. \
Perform the following steps:

* Create an OAuth access token on Quay with the right permissions
* Edit the following files:
  - `helm/pruner/values.yaml`
  - `helm/pruner/config.yaml`
* Install the Helm chart:
  ```
  $ helm install pruner helm/pruner/
  ```
## Usage
### Run the application manually on Openshift
Prerequisites:
* The procedure described in Deploy on OpenShift is completed with success.

Perform the following steps:

* Select the project where the application has been deployed
  ```
  $ oc project <project_name> # The name of the project is defined in the variable namespace of the file values.yaml
  ```
* Create a Job from the CronJob of the application
  ```
  $ oc create job --from=cronjob/quay-tags-pruner "quay-tags-pruner-$(date +%Y%m%d-%H%M)"
  ```
* View the logs of the pod created by the Job
  ```
  $ oc get pod
  $ oc logs <pod_name>
  ```

## Troubleshooting
This chapter describes some useful command to verify and check the previous executions of the quay-adm-pruner application

### Verify status and logs of the previous execution of the quay-adm-pruner

* Select the project where quay-adm-pruner has been deployed(defined in the variable "namespace" of the file
 helm/pruner/values.yaml)
```
$ oc project <project_name>
```

* View the past execution of the quay-adm-pruner listing the pods in the namespace

```
$ oc get pod
NAME                                 READY   STATUS      RESTARTS   AGE
quay-tags-pruner-27719910--1-d4wwz   0/1     Completed   0          9h
quay-tags-pruner-27720492--1-sjfdl   0/1     Completed   0          4m11s
quay-tags-pruner-27720494--1-pqdhf   0/1     Completed   0          2m11s
quay-tags-pruner-27720496--1-4hd6d   0/1     Error       0          11s
```

The following list report the description of the most common STATUS value:
1) Completed: The quay-adm-pruner application ended with success(status code: 0)
2) Error: The quay-adm-pruner application ended with an error(status code: 0)
3) Running: The quay-adm-pruner application is still running

* View the logs of the application quay-adm-pruner
```
  $ oc logs <pod_name>
```

* To analyze complex errors in pod logs could be useful to start a debug pod of the failed pod running with the same
  user(not root) used regularly from the application and run the application from the container

$ oc debug pod/<pod_name>
Starting pod/quay-tags-pruner-27720510--1-dvjpz-debug ...
sh-4.4$ python3.8 -u /usr/bin/pruner.py

* You can also start a debug pod with root access. quay-tags-pruner pod typically run with non-root privileges, but
  running troubleshooting pods with temporary root privileges can be useful during further issue investigation.

$ oc debug --as-root pod/<pod_name>
Starting pod/quay-tags-pruner-27720510--1-dvjpz-debug ...
sh-4.4$ python3.8 -u /usr/bin/pruner.py

## References

[1] https://access.redhat.com/documentation/en-us/red_hat_quay/3.6/html-single/use_red_hat_quay/index#create_oauth_access_token