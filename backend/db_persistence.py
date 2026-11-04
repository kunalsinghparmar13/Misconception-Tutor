import os


def commit_sqlite_volume():
    """
    Persist the SQLite database when running on Modal.
    Does nothing during local development.
    """
    volume_name = os.getenv("MODAL_DB_VOLUME")

    if not volume_name:
        return

    import modal

    volume = modal.Volume.from_name(volume_name)
    volume.commit()