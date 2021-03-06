'''
This module has things regarding a generic Sumo deployment.

@author: Weimin Ma
@contact: U{weimin@sumologic.com<mailto:weimin@sumologic.com>}
@since: 2016-04-25
'''
from abc import ABCMeta, abstractmethod, abstractproperty
from testingframework.exceptions import UnsupportedConnectorError
from testingframework.log import Logging
from testingframework.connector.base import Connector
from testingframework.connector.rest import RESTConnector
from testingframework.connector.service import ServiceConnector


class Sumo(Logging):
    '''
    Represents a Sumo deployment.
    This class is abstract and cannot be instantiated directly.

    @ivar connector_factory: The factory to use when creating the connector.
    @type connector_factory: function
    @ivar _default_connector: The default connector. Is None at first and is
                              later created when L{default_connector} is used.
    @type _default_connector: L{Connector}
    @ivar _start_listeners: A collection of start listeners
    @type _start_listeners: set
    @ivar name: The name of this instance. Defaults to the ID of this object.
    @type name: str
    @ivar _logger: The logger this instance uses.
    '''
    _username = 'Administrator'
    _password = ''
    _accessid = ''
    _accesskey = ''

    __metaclass__ = ABCMeta

    _CONNECTOR_TYPE_TO_CLASS_MAPPINGS = {Connector.REST: RESTConnector, Connector.SERVICEREST: ServiceConnector}

    def __init__(self, name):
        '''
        Creates a new Sumo deployment.
        '''
        self._default_connector = None
        self._start_listeners = set()
        self._connectors = {}

        self._name = name or id(self)

        Logging.__init__(self)

    def __str__(self):
        '''
        Casts this instance to a string.

        @return: The string representation of this object.
        @rtype: str
        '''
        return self._str_format.format(**self._str_format_arguments)

    @abstractproperty
    def _str_format(self):
        '''
        The format to use when casting this instance to a string.

        @rtype: str
        '''

    @abstractproperty
    def _str_format_arguments(self):
        '''
        The arguments for the L{_str_format} to use when casting this instance
        to a string.

        @rtype: dict
        '''

    @property
    def name(self):
        '''
        The name of this instance.

        @rtype: str
        '''
        return self._name

    @property
    def username(self):
        return self._username
    
    @username.setter
    def username(self, value):
        self._username=value

    @property
    def password(self):
        return self._password

    @password.setter
    def password(self, value):
        self._password=value
    
    @property
    def accessid(self):
        return self._accessid
    
    @username.setter
    def accessid(self, value):
        self._accessid=value

    @property
    def accesskey(self):
        return self._accesskey

    @password.setter
    def accesskey(self, value):
        self._accesskey=value

    def uri_base(self):
        return 'https://'

    def register_start_listener(self, listener):
        '''
        Adds a listener that will be notified when connection to Sumo is lost.

        The listener must be a function (respond to C{__call__} to be more
        precise)

        @param listener: The start listener
        @raise InvalidStartListener: If the listener is not callable.
        '''
        _validate_start_listener(listener)
        self._start_listeners.add(listener)

    def unregister_start_listener(self, listener):
        '''
        Removes the specified start listener.

        If the listener is not in the list this call has no effect.

        @param listener: The listener to remove
        '''
        try:
            self._start_listeners.remove(listener)
        except KeyError:
            pass

    def create_connector(self, contype=None, *args, **kwargs):
        '''
        Creates and returns a new connector of the type specified or
        REST connector if none specified

        This connector will not be logged in, for that see
        L{create_logged_in_connector}

        Any argument specified to this method will be passed to the connector's
        initialization method

        @param contype: Type of connector to create, defined in Connector class,
           defaults to Connector.REST

        @return: The newly created connector
        '''
        contype = contype or Connector.REST

        if contype not in self._CONNECTOR_TYPE_TO_CLASS_MAPPINGS:
            raise UnsupportedConnectorError

        conn = self._CONNECTOR_TYPE_TO_CLASS_MAPPINGS[contype](self,
                                                               *args,
                                                               **kwargs)

        connector_id = self._get_connector_id(contype=contype,
                                              user=conn.username)

        if connector_id in self._connectors.keys():
            self.logger.warn("Connector {id} is being replaced".format(
                id=connector_id))
            del self._connectors[connector_id]
        self._connectors[connector_id] = conn

        return self._connectors[connector_id]

    def create_logged_in_connector(self, set_as_default=None, contype=None,
                                   *args, **kwargs):
        '''
        Creates and returns a new connector of type specified or of type
        L{SDKConnector} if none specified.

        This method is identical to the L{create_connector} except that this
        method also logs the connector in.

        Any argument specified to this method will be passed to the connector's
        initialization method

        @param set_as_default: Determines whether the created connector is set
                               as the default connector too. True as default.
        @type bool
        @param contype: type of connector to create, available types defined in
            L{Connector} class. Connector.REST as default

        @return: The newly created, logged in, connector
        '''
        contype = contype or Connector.REST
        conn = self.create_connector(contype, *args, **kwargs)
        if set_as_default:
            self._default_connector = conn
        return conn

    def set_default_connector(self, contype, username):
        '''
        Sets the default connector to an already existing connector

        @param contype: type of connector, defined in L{Connector} class
        @param username: sumo username used by connector
        @type username: string
        '''
        self._default_connector = self.connector(contype, username)

    def remove_connector(self, contype, username):
        '''
        removes a  connector, sets default connector to None if removing the
        default connector

        @param contype: type of connector, defined in L{Connector} class
        @param username: sumo username used by connector
        @type username: string
        '''
        if self.default_connector == self.connector(contype, username):
            self._default_connector = None

        connector_id = self._get_connector_id(contype, username)
        del self._connectors[connector_id]

    def _get_connector_id(self, contype, user):
        '''
        Returns the connector id

        @param contype: type of connector, defined in L{Connector} class
        @param username: sumo username used by connector
        @type username: string
        '''
        connector_id = '{contype}:{user}'.format(contype=contype, user=user)
        return connector_id

    def set_credentials_to_use(self, username='Administrator', password='testing123@'):
        '''
        This method just initializes/updates self._username to username specified & self._password to password specified
        @param username: sumo username that gets assigned to _username property of sumo class
        @param password: sumo password for the above username.
        Note: This method won't create/update the actual credentials on the sumo deployment. 
        It is asssumed that credentials specified here are already valid credentials.
        '''
        self._username = username
        self._password = password

    @property
    def default_connector(self):
        '''
        Returns the default connector for this Sumo deployment.

        This method caches the value so it isn't created on every call.
        '''
        if self._default_connector is None:
            self._default_connector = self.create_logged_in_connector(
                set_as_default=True, username=self.username, password=self.password)
        return self._default_connector

    def connector(self, contype=None, username=None):
        '''
        Returns the connector specified by type and username, defaults to
        the default connector if none specified

        @param contype: type of connector, defined in L{Connector} class
        @param username: connector's username
        @type username: string
        '''
        if contype is None and username is None:
            return self.default_connector

        connector_id = self._get_connector_id(contype, username)
        if connector_id not in self._connectors.keys():
            raise InvalidConnector("Connector {id} does not exist".format(
                id=connector_id))

        return self._connectors[connector_id]

    def jobs(self, contype=None, username=None):
        '''
        Returns a Jobs manager that uses the specified connector. Defaults to
        default connector if none specified.

        This property creates a new Jobs manager each call so you may do as
        you please with it.

        @param contype: type of connector, defined in L{Connector} class
        @param username: connector's username
        @type username: string
        @rtype: L{Jobs}
        '''
        from testingframework.manager.jobs import Jobs
        return Jobs(self.connector(contype, username))


def _validate_start_listener(listener):
    '''
    Validates the start listener making sure it can be called.

    @param listener: The start listener
    @raise InvalidStartListener: If the listener is invalid
    '''
    if not _variable_is_a_function(listener):
        raise InvalidStartListener


def _variable_is_a_function(variable):
    '''
    Checks if a specified variable is a function by checking if it implements
    the __call__ method.

    This means that the object doesn't have to be a function to pass this
    function, just implement __call__

    @return: True if the variable is a function
    @rtype: bool
    '''
    return hasattr(variable, '__call__')


class InvalidConnector(KeyError):
    '''
    Raised when accessing an invalid connector
    '''
    pass
