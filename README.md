# quay-tags-pruner

Simple application to prune tags of images placed on a Red Hat Quay registry.

## Overview

This application:
  - searches the given list of organizations for images
  - scans the images for the desired tag patterns
  - for each tag pattern it deletes all the tags except for the N most recent
    tag revisions of every image

List of available variables:

```
rules:
  - organization_list:
      - org1
      - org2
    parameters:
    - tag_filter: "."
      keep_n_tags: "5"
      keep_tags_younger_than: "1y"
  - organization_list:
      - org3
    parameters:
    - tag_filter: "."
      keep_n_tags: "15"
      keep_tags_younger_than: "1y"

default_rule:
  enabled: True
  parameters:
    - tag_filter: "."
      keep_n_tags: "10"
      keep_tags_younger_than: "2y"
```

## Developing
### Create a developing environment on a workstation to run/debug the application without using container

The following command allows to configure the configuration files:

```
sudo mkdir -p /opt/conf/
USER=$(whoami) sudo chown $USER /opt/conf/
ln -s $PWD/helm/pruner/config.yaml /opt/conf/config.yaml
```

The following command execute the application:

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
