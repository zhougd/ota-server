"""CoAP management module."""

import os
import asyncio
import logging
import aiocoap.resource as resource

from aiocoap import Context, Message, CONTENT

from .firmware import get_info_from_filename

logger = logging.getLogger("otaserver")


COAP_PORT = 5683


class FirmwareBinaryResource(resource.Resource):
    """CoAP resource returning the latest firmware."""

    def __init__(self, controller, appid, slot):
        super(FirmwareBinaryResource, self).__init__()
        self._controller = controller
        self._appid = appid
        self._slot = slot

    @asyncio.coroutine
    def render_get(self, request):
        """Response to CoAP GET request."""
        try:
            remote = request.remote[0]
        except TypeError:
            remote = request.remote.sockaddr[0]

        logger.debug("CoAP GET received from {}".format(remote))

        firmware_binary = self._controller.\
            get_latest_firmware_binary(self._appid, self._slot)

        return Message(code=CONTENT, payload=firmware_binary)


class FirmwareVersionResource(resource.Resource):
    """CoAP resource returning the firmware latest version."""

    def __init__(self, controller, appid, slot):
        super(FirmwareVersionResource, self).__init__()
        self._controller = controller
        self._appid = appid
        self._slot = slot

    @asyncio.coroutine
    def render_get(self, request):
        """Response to CoAP GET request."""
        try:
            remote = request.remote[0]
        except TypeError:
            remote = request.remote.sockaddr[0]

        logger.debug("CoAP GET received from {}".format(remote))

        return Message(code=CONTENT,
                       payload=self._controller
                       .get_latest_firmware_version(
                       self._appid, self._slot).encode('ascii'))

class FirmwareNameResource(resource.Resource):
    """CoAP resource returning the firmware latest version filename."""

    def __init__(self, controller, appid, slot):
        super(FirmwareNameResource, self).__init__()
        self._controller = controller
        self._appid = appid
        self._slot = slot

    @asyncio.coroutine
    def render_get(self, request):
        """Response to CoAP GET request."""
        try:
            remote = request.remote[0]
        except TypeError:
            remote = request.remote.sockaddr[0]

        logger.debug("CoAP GET received from {}".format(remote))

        return Message(code=CONTENT,
                       payload=self._controller
                       .get_latest_firmware_filename(
                       self._appid, self._slot).encode('ascii'))

class CoapController():
    """CoAP controller with CoAP server inside."""

    def __init__(self, fw_path, port=COAP_PORT):
        self.port = port
        self.fw_path = fw_path
        self.root_coap = resource.Site()
        for filename in os.listdir(fw_path):
            self.add_resources(filename)
        asyncio.async(Context.create_server_context(self.root_coap,
                                                    bind=('::', self.port)))

    def add_resources(self, filename):
        """Add new resources for the given application id."""
        slot, app_id, _ = get_info_from_filename(filename)
        self.root_coap.add_resource((app_id, 'version',),
                                    FirmwareVersionResource(self,
                                                            app_id, slot))
        self.root_coap.add_resource((app_id, slot, 'name', ),
                                    FirmwareNameResource(self, app_id, slot))
        self.root_coap.add_resource((app_id, slot, 'firmware', ),
                                    FirmwareBinaryResource(self, app_id, slot))

    def get_latest_firmware_version(self, appid, slot):
        """Get the latest firmware version."""
        all_firmwares = os.listdir(self.fw_path)
        if all_firmwares == []:
            logger.warning('No firmware found')
            return ''

        all_versions = [int(get_info_from_filename(fw)[2], 16)
                        for fw in all_firmwares
                        if (get_info_from_filename(fw)[1] == appid and
                            get_info_from_filename(fw)[0] == slot)]

        if all_versions == []:
            logger.warning('No latest version found')
            return ''

        return str(hex(max(all_versions)))

    def get_latest_firmware_binary(self, appid, slot):
        """Get the latest firmware content."""
        filename = self.get_latest_firmware_filename(appid, slot)
        if not filename:
            logger.warning("No firmware filename found for application ID '{}'"
                           "and slot '{}'").format(appid, slot)
            return b''

        filename = os.path.join(self.fw_path, filename)

        if not os.path.isfile(filename):
            logger.warning("Firmware filename doesn't exists: '{}'"
                           .format(filename))
            return ''

        return open(filename, 'rb').read()


    def get_latest_firmware_filename(self, appid, slot):
        """Get the latest firmware content."""
        version = self.get_latest_firmware_version(appid, slot)
        if not version:
            logger.warning("version is empty")
            return ''

        info = set((slot, appid, version))

        match = [fw for fw in os.listdir(self.fw_path)
                 if set(get_info_from_filename(fw)) == info]

        if match == []:
            logger.warning("No firmware filename found for application ID '{}'"
                           ", slot '{}' and version {}"
                           .format(appid, slot, version))
            return ''

        return match[0]
