# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
import os

import awsiot.greengrasscoreipc.client as client
import config_utils
from awscrt.io import (
    ClientBootstrap,
    DefaultHostResolver,
    EventLoopGroup,
    SocketDomain,
    SocketOptions,
)
from awsiot.eventstreamrpc import Connection, LifecycleHandler, MessageAmendment
from awsiot.greengrasscoreipc.model import (
    QOS,
    ConfigurationUpdateEvents,
    GetConfigurationRequest,
    PublishToIoTCoreRequest,
    SubscribeToConfigurationUpdateRequest,
)


class IPCUtils:
    def connect(self):
        elg = EventLoopGroup()
        resolver = DefaultHostResolver(elg)
        bootstrap = ClientBootstrap(elg, resolver)
        socket_options = SocketOptions()
        socket_options.domain = SocketDomain.Local
        amender = MessageAmendment.create_static_authtoken_amender(os.getenv("SVCUID"))
        hostname = os.getenv("AWS_GG_NUCLEUS_DOMAIN_SOCKET_FILEPATH_FOR_COMPONENT")
        connection = Connection(
            host_name=hostname,
            port=8033,
            bootstrap=bootstrap,
            socket_options=socket_options,
            connect_message_amender=amender,
        )
        self.lifecycle_handler = LifecycleHandler()
        connect_future = connection.connect(self.lifecycle_handler)
        connect_future.result(config_utils.TIMEOUT)
        return connection

    def publish_results_to_cloud(self, PAYLOAD):
        r"""
        Ipc client creates a request and activates the operation to publish messages to the IoT core
        with a qos type over a topic.

        :param PAYLOAD: An dictionary object with inference results.
        """
        try:
            request = PublishToIoTCoreRequest(
                topic_name=config_utils.TOPIC,
                qos=config_utils.QOS_TYPE,
                payload=json.dumps(PAYLOAD).encode(),
            )
            operation = ipc_client.new_publish_to_iot_core()
            operation.activate(request).result(config_utils.TIMEOUT)
            config_utils.logger.info("Publishing results to the IoT core...")
            operation.get_response().result(config_utils.TIMEOUT)
        except Exception as e:
            config_utils.logger.error("Exception occured during publish: {}".format(e))

    def publish_metadata_to_cloud(self, METADATA):
        r"""
        Ipc client creates a request and activates the operation to publish messages to the IoT core
        with a qos type over a topic.

        :param METADATA: An dictionary object with inference results.
        """
        try:
            request = PublishToIoTCoreRequest(
                topic_name=config_utils.TOPIC,  #TODO: Try to use two different topics to publish different request, but failed. I guess its because The IPC client can't send new requests or process new event messages while the thread is blocked. You can run blocking code in a separate thread that you run from the handler function. Blocking code includes sleep calls, loops that continuously run, and synchronous I/O requests that take time to complete. See https://docs.aws.amazon.com/greengrass/v2/developerguide/interprocess-communication.html.
                qos=config_utils.QOS_TYPE,  
                payload=json.dumps(METADATA).encode(),
            )
            operation = ipc_client.new_publish_to_iot_core()
            operation.activate(request).result(config_utils.TIMEOUT)
            config_utils.logger.info("Publishing metadata to the IoT core...")
            operation.get_response().result(config_utils.TIMEOUT)
        except Exception as e:
            config_utils.logger.error("Exception occured during publish: {}".format(e))

    def get_configuration(self):
        r"""
        Ipc client creates a request and activates the operation to get the configuration of
        inference component passed in its recipe.

        :return: A dictionary object of DefaultConfiguration from the recipe.
        """
        try:
            request = GetConfigurationRequest()
            operation = ipc_client.new_get_configuration()
            operation.activate(request).result(config_utils.TIMEOUT)
            result = operation.get_response().result(config_utils.TIMEOUT)
            return result.value
        except Exception as e:
            config_utils.logger.error(
                "Exception occured during fetching the configuration: {}".format(e)
            )
            exit(1)

    def get_config_updates(self):
        r"""
        Ipc client creates a request and activates the operation to subscribe to the configuration changes.
        """
        try:
            subsreq = SubscribeToConfigurationUpdateRequest()
            subscribe_operation = ipc_client.new_subscribe_to_configuration_update(
                ConfigUpdateHandler()
            )
            subscribe_operation.activate(subsreq).result(config_utils.TIMEOUT)
            subscribe_operation.get_response().result(config_utils.TIMEOUT)
        except Exception as e:
            config_utils.logger.error(
                "Exception occured during fetching the configuration updates: {}".format(e)
            )
            exit(1)


class ConfigUpdateHandler(client.SubscribeToConfigurationUpdateStreamHandler):
    r"""
    Custom handle of the subscribed configuration events(steam,error and close).
    Due to the SDK limitation, another request from within this callback cannot to be sent.
    Here, it just logs the event details, updates the updated_config to true.
    """

    def on_stream_event(self, event: ConfigurationUpdateEvents) -> None:
        config_utils.logger.info(event.configuration_update_event)
        config_utils.UPDATED_CONFIG = True

    def on_stream_error(self, error: Exception) -> bool:
        config_utils.logger.error("Error in config update subscriber - {0}".format(error))
        return False

    def on_stream_closed(self) -> None:
        config_utils.logger.info("Config update subscription stream was closed")


# Get the ipc client
try:
    ipc_client = client.GreengrassCoreIPCClient(IPCUtils().connect())
    config_utils.logger.info("Created IPC client...")
except Exception as e:
    config_utils.logger.error(
        "Exception occured during the creation of an IPC client: {}".format(e)
    )
    exit(1)
