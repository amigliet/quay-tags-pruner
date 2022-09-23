import pruner


def test_get_repos_json(requests_mock):
    """Test retrieval of a list of repositories."""
    requests_mock.get(
        "https://quay.example.org/api/v1/repository?namespace=myorg",
        json={"repositories": []}
    )
    quay_url = 'quay.example.org'
    quay_org = "myorg"
    token = "d34db33f"
    repos = pruner.get_repo_list_json(quay_url, token, quay_org)
    assert repos == {"repositories": []}


def test_get_tags_json(requests_mock):
    """Test the retrieval of a list of tags."""
    requests_mock.get(
        "https://quay.example.org/api/v1/repository/myorg/myimage/tag/",
        json={
            "has_additional": False,
            "page": 1,
            "tags": [
                {
                    "name": "latest", "reversion": False,
                    "start_ts": 1558262258,
                    "image_id": "123",
                    "last_modified": "Sun, 19 May 2019 10:37:38 -0000",
                    "manifest_digest": (
                        "sha256:"
                        "3222549da9edd114770975510e425674"
                        "282d176e19af1e24a40a2b846cb5a925"
                    ),
                    "docker_image_id": "321",
                    "is_manifest_list": False,
                    "size": 49165450
                }
            ]
        }
    )
    quay_url = 'quay.example.org'
    quay_org = "myorg"
    token = "d34db33f"
    image_name = "myimage"
    tags = pruner.get_tags_json(quay_url, token, quay_org, image_name)
    assert tags['tags'][0]["name"] == "latest"


def test_tags_to_remove():
    payload = {
        "has_additional": False,
        "page": 1,
        "tags": [
            {
                "name": "latest",
                "reversion": False,
                "start_ts": 1558262258,
                "image_id": "123",
                "last_modified": "Sun, 19 May 2019 10:37:38 -0000",
                "manifest_digest": (
                    "sha256:"
                    "3222549da9edd114770975510e425674"
                    "282d176e19af1e24a40a2b846cb5a925"
                ),
                "docker_image_id": "321",
                "is_manifest_list": False,
                "size": 49165450
            },
            {
                "name": "1.1.0-final", "reversion": False,
                "start_ts": 1558261258,
                "image_id": "122",
                "last_modified": "Sun, 18 May 2019 10:37:38 -0000",
                "manifest_digest": (
                    "sha256:"
                    "3222549da9edd114770975510e425674"
                    "282d176e19af1e24a40a2b846cb5a925"
                ),
                "docker_image_id": "320",
                "is_manifest_list": False,
                "size": 49165450
            },
            {
                "name": "1.1.0-rc1", "reversion": False,
                "start_ts": 1558260258,
                "image_id": "121",
                "last_modified": "Sun, 17 May 2019 10:37:38 -0000",
                "manifest_digest": (
                    "sha256:"
                    "3222549da9edd114770975510e425674"
                    "282d176e19af1e24a40a2b846cb5a925"
                ),
                "docker_image_id": "319",
                "is_manifest_list": False,
                "size": 49165450
            },
            {
                "name": "1.0.0-rc1", "reversion": False,
                "start_ts": 1558260258,
                "image_id": "121",
                "last_modified": "Sun, 17 May 2019 10:37:38 -0000",
                "manifest_digest": (
                    "sha256:"
                    "3222549da9edd114770975510e425674"
                    "282d176e19af1e24a40a2b846cb5a925"
                ),
                "docker_image_id": "319",
                "is_manifest_list": False,
                "size": 49165450
            }
        ]
    }
    filtered_tags = pruner.select_tags_to_remove(payload, r'-rc\d+$', 0)
    assert len(filtered_tags) == 2
    assert all('-rc' in tag['name'] for tag in filtered_tags)


def test_delete_tags(requests_mock):
    requests_mock.delete(
        (
            "https://quay.example.org/api/v1"
            "/repository/myorg/myimage/tag/1.0.0-rc1"
        ),

    )
    tags_to_remove = [
        {
            "name": "1.0.0-rc1", "reversion": False,
            "start_ts": 1558260258,
            "image_id": "121",
            "last_modified": "Sun, 17 May 2019 10:37:38 -0000",
            "manifest_digest": (
                "sha256:"
                "3222549da9edd114770975510e425674"
                "282d176e19af1e24a40a2b846cb5a925"
            ),
            "docker_image_id": "319",
            "is_manifest_list": False,
            "size": 49165450
        }
    ]
    quay_url = 'quay.example.org'
    quay_org = "myorg"
    token = "d34db33f"
    image_name = "myimage"
    pruner.delete_tags(quay_url, token, quay_org, image_name, tags_to_remove)
