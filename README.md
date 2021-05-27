# quay-tags-pruner

Simple application to prune tags of images placed on a Red Hat Quay registry.

## Overview

This application scans all the images present in a list of organizations and
for each image it keeps only the latest N tags that match a specific pattern.

List of available variables:

```
{
    "vars": {
        "debug": "True",
        "dry_run": "False",
        "quay_url": "example-quay-quay-registry.apps.cluster-name.base-domain.com",
        "keep_tag_number": "5",
        "tag_pattern": ".",
        "quay_orgs": [
            "library",
            "amigliet"
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
