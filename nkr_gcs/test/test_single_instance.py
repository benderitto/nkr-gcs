from nkr_gcs.app import acquire_instance_lock


def test_only_one_instance_lock_can_be_held(tmp_path):
    path = tmp_path / "instance.lock"
    first = acquire_instance_lock(path)
    assert first is not None
    assert acquire_instance_lock(path) is None

    first.unlock()
    replacement = acquire_instance_lock(path)
    assert replacement is not None
    replacement.unlock()
