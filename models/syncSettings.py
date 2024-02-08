class SyncSettings:
    def __init__(self):
        self.downloadMissingFiles = True
        self.uploadUnsyncedFiles = True
        self.deleteUnsyncedFiles = True
        self.deleteMissingFiles = True
        self.deletePlaceholderFiles = True
        self.deleteEmptyFolders = True
    
    def __str__(self):
        return f"downloadMissingFiles: {self.downloadMissingFiles}, uploadUnsyncedFiles: {self.uploadUnsyncedFiles}, deleteUnsyncedFiles: {self.deleteUnsyncedFiles}, deleteMissingFiles: {self.deleteMissingFiles}, deletePlaceholderFiles: {self.deletePlaceholderFiles}, deleteEmptyFolders: {self.deleteEmptyFolders}"
