from typing import Optional, List

from docker.models.containers import Container
from docker.models.images import Image

from wrapper.model.SelectableInterface import SelectableInterface
from wrapper.utils.ConstantConfig import ConstantConfig
from wrapper.utils.ExeLog import logger


# Class of an exegol image
class ExegolImage(SelectableInterface):

    def __init__(self,
                 name: str = "NONAME",
                 digest: Optional[str] = None,
                 image_id: Optional[str] = None,
                 size: int = 0,
                 docker_image: Optional[Image] = None):
        """Docker image default value"""
        # Init attributes
        self.__image: Image = docker_image
        self.__name: str = name
        self.__version_specific: bool = "-" in name
        self.__profile_version: str = '-'.join(
            name.split('-')[1:]) if self.isVersionSpecific() else "[bright_black]N/A[/bright_black]"
        self.__image_version: str = self.__profile_version
        # Remote image size
        self.__dl_size: str = ":question:" if size == 0 else self.__processSize(size)
        # Local uncompressed image's size
        self.__disk_size: str = ":question:"
        # Remote image ID
        self.__digest: str = "[bright_black]:question:[/bright_black]"
        # Local docker image ID
        self.__image_id: str = "[bright_black]Not installed[/bright_black]"
        # Status
        self.__is_remote: bool = size > 0
        self.__is_install: bool = False
        self.__is_update: bool = False
        self.__is_discontinued: bool = False
        # The latest version is merged with the latest one, every other version are old and must be removed
        self.__must_be_removed: bool = self.__version_specific
        self.__custom_status: str = ""
        # Process data
        if docker_image is not None:
            self.__initFromDockerImage()
        else:
            self.__setDigest(digest)
            self.__setImageId(image_id)
        logger.debug("└── {}\t→ ({}) {}".format(self.__name, self.getType(), self.__digest))

    def __initFromDockerImage(self):
        """Parse Docker object to set up self configuration on creation."""
        # If docker object exist, image is already installed
        self.__is_install = True
        # Set init values from docker object
        if len(self.__image.attrs["RepoTags"]) > 0:
            # Tag as deprecated until the latest tag is found
            self.__must_be_removed = True
            name = self.__name  # Init with old name
            self.__name = None
            for repo_tag in self.__image.attrs["RepoTags"]:
                repo, name = repo_tag.split(':')
                if not repo.startswith(ConstantConfig.IMAGE_NAME):
                    # Ignoring external images (set container using external image as deprecated)
                    continue
                # Check if a non-version tag (the latest tag) is supplied, if so, this image must NOT be removed
                if "-" not in name:
                    self.__must_be_removed = False
                    self.__name = name
                else:
                    self.__image_version: str = '-'.join(name.split('-')[1:])
            # if no version has been found, restoring previous name
            if self.__name is None:
                self.__name = name
        else:
            # If tag is <none>, use default value
            self.__name = "<none>"  # TODO find attached container
            self.__must_be_removed = True
        self.__setRealSize(self.__image.attrs["Size"])
        # Set local image ID
        self.__setImageId(self.__image.attrs["Id"])
        # If this image is remote, set digest ID
        self.__is_remote = len(self.__image.attrs["RepoDigests"]) > 0
        if self.__is_remote:
            self.__setDigest(self.__parseDigest(self.__image))

    def syncContainer(self, container: Container):
        """Synchronization between the container and the image.
        If the image has been updated, the tag is lost,
        but it is saved in the properties of the container that still uses it."""
        if self.isLocked():
            self.__name = f'{container.attrs["Config"]["Image"].split(":")[1]} ' \
                          f'[bright_black](deprecated{f" v{self.getImageVersion()}" if "N/A" not in self.getImageVersion() else ""})[/bright_black]'
            # TODO debug deprecated version number

    def updateCheck(self) -> Optional[str]:
        """If this image can be updated, return his name, otherwise return None"""
        if self.__is_remote:
            if self.__is_update:
                logger.warning("This image is already up to date. Skipping.")
                return None
            return self.__name
        else:
            logger.error("Local images cannot be updated.")
            return None

    def isUpToDate(self) -> bool:
        if not self.__is_remote:
            return True  # Local image cannot be updated
        return self.__is_update

    def removeCheck(self) -> Optional[str]:
        """If this image can be removed, return his name, otherwise return None"""
        if self.__is_install:
            return self.__name
        else:
            logger.error("This image is not installed locally. Skipping.")
            return None

    def setDockerObject(self, docker_image: Image):
        """Docker object setter. Parse object to set up self configuration."""
        self.__image = docker_image
        # When a docker image exist, image is locally installed
        self.__is_install = True
        # Set real size on disk
        self.__setRealSize(self.__image.attrs["Size"])
        # Set local image ID
        self.__setImageId(docker_image.attrs["Id"])
        # Check if local image is sync with remote digest id (check up-to-date status)
        self.__is_update = self.__digest == self.__parseDigest(docker_image)
        # Add version tag (if available)
        for repo_tag in docker_image.attrs["RepoTags"]:
            tmp_name, tmp_tag = repo_tag.split(':')
            if tmp_name == ConstantConfig.IMAGE_NAME and "-" in repo_tag:
                self.__image_version = '-'.join(repo_tag.split('-')[1:])

    @classmethod
    def __mergeCommonImages(cls, images: List['ExegolImage']):
        """Select latest images and merge them with their version specific equivalent (installed and/or latest)."""
        latest_images, version_images = [], []
        # Splitting images by type : latest or version specific
        for img in images:
            if '-' in img.getName():
                version_images.append(img)
            else:
                latest_images.append(img)

        # Test each combination
        for main_image in latest_images:
            for version_specific in version_images:
                match = False
                if main_image.getRemoteId() == version_specific.getRemoteId():
                    # Set exact profile version to the remaining latest image
                    main_image.__setLatestVersion(version_specific.getImageVersion())
                    match = True
                # Try to find a matching version (If 2 local id images are the same, this version is actually installed as latest)
                if main_image.getLocalId() == version_specific.getLocalId():
                    # Set version to the remaining latest image
                    main_image.__setImageVersion(version_specific.getImageVersion())
                    match = True
                if match:
                    try:
                        # Remove duplicates image from the result array (don't need to be returned, same object)
                        images.remove(version_specific)
                    except ValueError:
                        # already been removed
                        pass

    @classmethod
    def mergeImages(cls, remote_images: List['ExegolImage'], local_images: List[Image]) -> List['ExegolImage']:
        """Compare and merge local images and remote images.
        Use case to process :
            - up-to-date : Version specific image can use exact digest_id matching. Latest image must match corresponding tag
            - outdated : Don't match digest_id but match (latest) tag
            - local image : don't have any 'RepoDigests' because they are local
            - discontinued : image with 'RepoDigests' properties but not found in remote
            - unknown : no internet connection = no information from the registry
            - not install : other remote images without any match
        Return a list of ExegolImage."""
        results = []
        # build data
        local_data = {}
        for local_img in local_images:
            # Check if custom local build
            if len(local_img.attrs["RepoDigests"]) == 0:
                # This image is build locally
                new_image = ExegolImage(docker_image=local_img)
                results.append(new_image)
                continue
            # find digest id
            digest = local_img.attrs["RepoDigests"][0].split('@')[1]
            for digest_id in local_img.attrs["RepoDigests"]:
                if digest_id.startswith(ConstantConfig.IMAGE_NAME):  # Find digest id from the right repository
                    digest = digest_id.split('@')[1]
                    break
            # Load variables - find current image tags
            names: List[str] = []
            tags: List[str] = []
            # handle tag
            if len(local_img.attrs["RepoTags"]) > 0:
                for repo_tag in local_img.attrs["RepoTags"]:
                    tmp_name, tmp_tag = repo_tag.split(':')
                    # Selecting tags from the good repository + filtering out version tag (handle by digest_id earlier)
                    if tmp_name == ConstantConfig.IMAGE_NAME and "-" not in tmp_tag:
                        names.append(tmp_name)
                        tags.append(tmp_tag)
            # Temporary data structure
            local_data[digest] = {"tags": tags, "image": local_img, "match": False}

        for current_image in remote_images:
            for digest, data in local_data.items():
                # Same digest id = up-to-date
                if current_image.getRemoteId() == digest:
                    current_image.setDockerObject(data["image"])  # Handle up-to-date, version specific
                    data["match"] = True
                    if current_image.isVersionSpecific():  # If the image is latest, tag must be also check
                        break
                # if latest mode, must match with tag (to find already installed outdated version)
                for tag in data.get('tags', []):
                    # Check if the tag is matching and
                    if current_image.getName() == tag and not current_image.isUpToDate():
                        current_image.setDockerObject(
                            data["image"])  # Handle latest image matching (up-to-date / outdated)
                        data["match"] = True
            # If remote image don't find any match, fallback to default => not installed

        results.extend(remote_images)  # Every remote images is kept (even if not installed)

        for data in local_data.values():
            if not data["match"]:
                # Matching image not found - there is no match with remote image list
                new_image = ExegolImage(docker_image=data["image"])
                if len(remote_images) == 0:
                    # If there are no remote images left, the user probably doesn't have internet and can't know the status of the images from the registry
                    new_image.setCustomStatus("[bright_black]Unknown[/bright_black]")
                else:
                    # If there are still remote images but the image has not found any match it is because it has been deleted/discontinued
                    new_image.__is_discontinued = True
                results.append(new_image)

        cls.__mergeCommonImages(results)
        return results

    @staticmethod
    def __processSize(size: int, precision: int = 1) -> str:
        """Text formatter from size number to human-readable size."""
        # https://stackoverflow.com/a/32009595
        suffixes = ["B", "KB", "MB", "GB", "TB"]
        suffix_index = 0
        calc: float = size
        while calc > 1024 and suffix_index < 4:
            suffix_index += 1  # increment the index of the suffix
            calc = calc / 1024  # apply the division
        return "%.*f%s" % (precision, calc, suffixes[suffix_index])

    def __eq__(self, other):
        """Operation == overloading for ExegolImage object"""
        # How to compare two ExegolImage
        if type(other) is ExegolImage:
            return self.__name == other.__name and self.__digest == other.__digest
        # How to compare ExegolImage with str
        elif type(other) is str:
            return self.__name == other
        else:
            logger.error(f"Error, {type(other)} compare to ExegolImage is not implemented")
            raise NotImplementedError

    def __str__(self):
        """Default object text formatter, debug only"""
        return f"{self.__name} ({self.__image_version}/{self.__profile_version}) - {self.__disk_size} - " + \
               (f"({self.getStatus()}, {self.__dl_size})" if self.__is_remote else f"{self.getStatus()}")

    def setCustomStatus(self, status: str):
        """Manual image's status overwrite"""
        self.__custom_status = status

    def getStatus(self) -> str:
        """Formatted text getter of image's status."""
        if self.__custom_status != "":
            return self.__custom_status
        elif not self.__is_remote:
            return "[blue]Local image[/blue]"
        elif self.__must_be_removed and self.__is_install:
            return "[red]Must be removed[/red]"
        elif self.__is_discontinued:
            return "[red]Discontinued[/red]"
        elif self.__is_update:
            return "[green]Up to date[/green]"
        elif self.__is_install:
            return f"[orange3]Update available ({self.getLatestVersion()})[/orange3]"
        else:
            return "[bright_black]Not installed[/bright_black]"

    def getType(self) -> str:
        """Image type getter"""
        return "remote" if self.__is_remote else "local"

    def __setDigest(self, digest: str):
        """Remote image digest setter"""
        if digest is not None:
            self.__digest = digest

    @staticmethod
    def __parseDigest(docker_image: Image) -> str:
        """Remote image digest setter"""
        for digest_id in docker_image.attrs["RepoDigests"]:
            if digest_id.startswith(ConstantConfig.IMAGE_NAME):  # Find digest id from the right repository
                return digest_id.split('@')[1]
        return ""

    def getRemoteId(self) -> str:
        """Remote digest getter"""
        return self.__digest

    def __setImageId(self, image_id: Optional[str]):
        """Local image id setter"""
        if image_id is not None:
            self.__image_id = image_id.split(":")[1][:12]

    def getLocalId(self) -> str:
        """Local id getter"""
        return self.__image_id

    def getKey(self) -> str:
        """Universal unique key getter (from SelectableInterface)"""
        return self.getName()

    def __setRealSize(self, value: int):
        """On-Disk image size setter"""
        self.__disk_size = self.__processSize(value)

    def getRealSize(self) -> str:
        """On-Disk size getter"""
        return self.__disk_size

    def getDownloadSize(self) -> str:
        """Remote size getter"""
        if not self.__is_remote:
            return "local"
        return self.__dl_size

    def getSize(self) -> str:
        """Image size getter. If the image is installed, return the on-disk size, otherwise return the remote size"""
        return self.__disk_size if self.__is_install else self.__dl_size

    def isInstall(self) -> bool:
        """Installation status getter"""
        return self.__is_install

    def isLocal(self) -> bool:
        """Local type getter"""
        return not self.__is_remote

    def isLocked(self) -> bool:
        """Current image is locked and must be removed getter"""
        return self.__must_be_removed

    def isVersionSpecific(self) -> bool:
        """Is the current image a version specific version.
        Image version specific container a '-' in the name,
        latest image don't."""
        return self.__version_specific

    def isLatest(self) -> bool:
        """Check if the current image is the latest tag"""
        return not self.__version_specific

    def getName(self) -> str:
        """Image's tag name getter"""
        return self.__name

    def __setImageVersion(self, version: str):
        """Image's tag version setter"""
        self.__image_version = version

    def getImageVersion(self) -> str:
        """Image's tag version getter"""
        return self.__image_version

    def __setLatestVersion(self, version: str):
        """Image's tag version setter"""
        self.__profile_version = version

    def getLatestVersion(self) -> str:
        """Latest image version getter"""
        return self.__profile_version

    def getFullName(self) -> str:
        """Dockerhub image's full name getter"""
        return f"{ConstantConfig.IMAGE_NAME}:{self.__name}"
