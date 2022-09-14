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
  that accepts only two values "True" or "False"

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
    # Keep the tags containing the string "prod" in their name uploaded before 120 days ago of each reposities of the
    # organization "org4" but delete all the other tags containing the string "prod" in their name of these repositories
    - tag_filter: "prod"
      keep_tags_younger_than: "120"
    # Keep the tags containing the string "test" in their name uploaded before 60 days ago of each reposities of the
    # organization "org4" but delete all the other tags containing the string "prod" in their name of these repositories
    # Note: all the tags not containing in their name the string "prod" or "test" will not be touched
    - tag_filter: "test"
      keep_tags_younger_than: "60"
default_rule:
  enabled: False
  parameters:
    - tag_filter: "."
      keep_n_tags: "10"
      keep_tags_younger_than: "90"
```

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