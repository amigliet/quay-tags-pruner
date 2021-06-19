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
    repos = pruner.get_repos_json(quay_url, token, quay_org)
    assert repos == {"repositories": []}
