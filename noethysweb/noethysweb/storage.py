from django.contrib.staticfiles.storage import ManifestStaticFilesStorage
import logging

logger = logging.getLogger(__name__)

class ForgivingManifestStaticFilesStorage(ManifestStaticFilesStorage):

    manifest_strict = False

    def hashed_name(self, name, content=None, filename=None):
        try:
            result = super().hashed_name(name, content, filename)
        except ValueError:
            # When the fille is missing, let's forgive and ignore that.
            logger.warning(f"Static file '{name}' is missing. Returning original name without hashing.")
            result = name
        return result
