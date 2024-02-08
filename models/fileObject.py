from dataclasses import dataclass
from typing import Any

""" Example json:

{
    "ChecksumAlgorithm": null,
    "ETag": "\"79dd001fca63cbeb8cd9f0a585744886\"",
    "Key": "vcx33oy8b86eg02/429086.png",
    "LastModified": "2023-12-08T07:01:00.495Z",
    "Owner": null,
    "RestoreStatus": null,
    "Size": 136235,
    "StorageClass": "STANDARD"
}
 """

@dataclass
class FileObject:
    ETag: str
    Key: str
    LastModified: str
    Size: int
    StorageClass: str

    @staticmethod
    def from_dict(obj: Any) -> 'FileObject':
        _ETag = str(obj.get("ETag"))
        _Key = str(obj.get("Key"))
        _LastModified = str(obj.get("LastModified"))
        _Size = int(obj.get("Size"))
        _StorageClass = str(obj.get("StorageClass"))
        return FileObject(_ETag, _Key, _LastModified, _Size, _StorageClass)