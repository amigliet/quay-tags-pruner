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
{
    "vars": {
        "debug": "True",
        "dry_run": "False",
        "quay_url": "example-quay-quay-registry.apps.cluster-name.base-domain.com",
        "quay_orgs": [
            "library",
            "amigliet"
        ],
        "tags": [
            {
                "pattern": ".",
                "revisions": "5"
            }
        ]
    }
}
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
  - `helm/pruner/config.json`
* Install the Helm chart:
  ```
  $ helm install pruner helm/pruner/
  ```
