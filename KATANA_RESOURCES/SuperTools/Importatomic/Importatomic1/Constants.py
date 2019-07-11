IMPORTATOMIC_VERSION = 1.0

NAME_COLUMN = 0
TASK_COLUMN = 1
VERSION_COLUMN = 2
FINALABLE_COLUMN = 3
RMAN_VERSION_COLUMN = 4
SHOT_COLUMN = 5


import sys
import os
import pickle
import logging

from UI4.Util.IconManager import GetIcon

log = logging.getLogger("Importatomic.Constants")


class LocationPaths(object):
    kRoot = "/root/world"
    kGeometry = kRoot + "/geo"
    kCamera = kRoot + "/cam"
    kKlf = "looks"
    kInstancer = kRoot + "/instances"


class ParamEnum(object):
    kNodeVersion = "__pluginRevision"
    kUser = "user"
    kAsset = "asset"
    kAbcAsset = "abcAsset"
    kLocation = "scengraphLocation"
    kPublishId = "sgPublishId"
    kAssetInfo = "assetInfo"
    kNamespace = "%s.namespace" % kAssetInfo
    kTaskType = "%s.taskType" % kAssetInfo
    kTask = "%s.task" % kAssetInfo
    kVersion = "%s.version" % kAssetInfo
    kIsFromShot = "%s.fromShot" % kAssetInfo
    kShot = "%s.shot" % kAssetInfo
    kHandlerType = "%s.handlerType" % kAssetInfo
    kEntityId = "%s.entityId" % kAssetInfo
    kIsFinalable = "%s.isFinalable" % kAssetInfo
    kUpdateHandler = "%s.updateHandler" % kAssetInfo


# TODO: Maybe Reorganize -- should come directly from handlers
class PublishTypes(object):
    kNone = None
    kAlembic = "Alembic Cache"
    kHoudiniAlembic = "Houdini Alembic Cache"
    kCamera = "Camera"
    kKlf = "Katana Look File Publish"
    kSurfCam = "Alembic Surface Camera Cache"
    kXgen = "XGen Hair Description"
    kXgenDelta = "XGen Manifest Deltas"
    kEfx = "Houdini Publish List"
    kInstancer = "XGen Instance info"


class NodeTypes(object):
    kNone = ""
    kImportatomic = "Importatomic"
    kBase = "ImportatomicBase"
    kAlembic = "AlembicHandler"
    kCamera = "CameraHandler"
    kUv = "UvHandler"
    kKlf = "KlfHandler"
    kXgen = "XgenHandler"
    kXgenDelta = "XgenDeltaHandler"
    kEfx = "OpenVdbHandler"
    kInstancer = "InstanceHandler"
    kAlembicIn = "Alembic_In_Prman" if int(float(os.getenv("RENDERMAN_VERSION", 21.8))) >= 22 else "Alembic_In"


# TODO: Get Icons directly from handler
class IconPaths(object):
    kHandlerDir = os.path.join(os.path.dirname(__file__), "Resources", "HandlerIcons")
    kAlembic = os.path.join(kHandlerDir, 'abc.png')
    kKlf = os.path.join(kHandlerDir, 'klf.png')
    kCamera = os.path.join(kHandlerDir, 'cam.png')
    kUv = os.path.join(kHandlerDir, 'uv.png')
    kXgen = os.path.join(kHandlerDir, 'xgen.png')
    kXgenDelta = os.path.join(kHandlerDir, 'xgd.png')
    kEfx = os.path.join(kHandlerDir, 'efx.png')
    kInstancer = os.path.join(kHandlerDir, 'inst.png')
    kCrowds = os.path.join(kHandlerDir, 'crowds.png')
    kCsGolaemCache = os.path.join(kHandlerDir, 'crowdsGolaemCache.png')

    kIconDir = os.path.join(os.path.dirname(__file__), "Resources", "Icons")
    kApproved = os.path.join(kIconDir, 'approved.png')
    kLatestNotApproved = os.path.join(kIconDir, 'latestNotApproved.png')
    kApprovedNotLatest = os.path.join(kIconDir, 'approvedNotLatest.png')
    kNotApprovedNotLatest = os.path.join(kIconDir, 'notApprovedNotLatest.png')
    kInvalid = os.path.join(kIconDir, 'invalid.png')
    kEmpty = os.path.join(kIconDir, 'empty.png')
