import io
from azure.storage.blob import BlobServiceClient
from fastapi import HTTPException, status
from app.config import settings

class StorageManager:
    """Manages secure corporate file archiving within Azure Blob Storage."""
    def __init__(self):
        try:
            self.blob_service_client = BlobServiceClient.from_connection_string(
                settings.AZURE_STORAGE_CONNECTION_STRING
            )
        except Exception as e:
            # Prevent app from crashing silently if storage link fails
            self.blob_service_client = None

    def upload_file(self, container_name: str, blob_name: str, file_bytes: bytes) -> str:
        """Uploads raw binary bytes and returns a dedicated path asset link."""
        if not self.blob_service_client:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Cloud storage service is currently offline."
            )
        try:
            container_client = self.blob_service_client.get_container_client(container_name)
            
            # Create container automatically if it does not exist yet
            if not container_client.exists():
                container_client.create_container()

            blob_client = container_client.get_blob_client(blob_name)
            blob_client.upload_blob(file_bytes, overwrite=True)
            return blob_client.url
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to stream document to Azure: {str(e)}"
            )

# Instantiated once for global import across target modules
storage_manager = StorageManager()
