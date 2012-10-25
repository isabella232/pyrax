#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2012 Rackspace

# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from pyrax.client import BaseClient
import pyrax.exceptions as exc
from pyrax.manager import BaseManager
from pyrax.resource import BaseResource
import pyrax.utils as utils


def assure_instance(fnc):
    def _wrapped(self, instance, *args, **kwargs):
        if not isinstance(instance, CloudDatabaseInstance):
            # Must be the ID
            instance = self._manager.get(instance)
        return fnc(self, instance, *args, **kwargs)
    return _wrapped


class CloudDatabaseInstance(BaseResource):
    def __init__(self, *args, **kwargs):
        super(CloudDatabaseInstance, self).__init__(*args, **kwargs)
        self._database_manager = BaseManager(self.manager.api,
                resource_class=CloudDatabaseDatabase, response_key="database",
                uri_base="instances/%s/databases" % self.id)
        self._user_manager = BaseManager(self.manager.api,
                resource_class=CloudDatabaseUser, response_key="user",
                uri_base="instances/%s/users" % self.id)


    def list_databases(self):
        """Returns a list of the names of all databases for this instance."""
        return self._database_manager.list()


    def list_users(self):
        """Returns a list of the names of all users for this instance."""
        return self._user_manager.list()


    def create_database(self, name, character_set=None, collate=None):
        """
        Creates a database with the specified name. If a database with
        that name already exists, a BadRequest (400) exception will
        be raised.
        """
        if character_set is None:
            character_set = "utf8"
        if collate is None:
            collate = "utf8_general_ci"
        # Note that passing in non-None values is required for the create_body
        # method to distinguish between this and the request to create and instance.
        self._database_manager.create(name=name, character_set=character_set,
                collate=collate, return_none=True)
        # Since the API doesn't return the info for creating the database object, we
        # have to do it manually.
        return self._database_manager.find(name=name)


    def create_user(self, name, password, database_names):
        """
        Creates a user with the specified name and password, and gives that
        user access to the spcified database(s).

        If a user with
        that name already exists, a BadRequest (400) exception will
        be raised.
        """
        if not isinstance(database_names, list):
            database_names = [database_names]
        # The API only accepts names, not DB objects
        database_names = [db if isinstance(db, basestring) else db.name
                for db in database_names]
        # Note that passing in non-None values is required for the create_body
        # method to distinguish between this and the request to create and instance.
        self._user_manager.create(name=name, password=password,
                database_names=database_names, return_none=True)
        # Since the API doesn't return the info for creating the user object, we
        # have to do it manually.
        return self._user_manager.find(name=name)


    def delete_database(self, name):
        """
        Deletes the specified database. If no database by that name
        exists, no exception will be raised; instead, nothing at all
        is done.
        """
        self._database_manager.delete(name)


    def delete_user(self, name):
        """
        Deletes the specified user. If no user by that name
        exists, no exception will be raised; instead, nothing at all
        is done.
        """
        self._user_manager.delete(name)


    def enable_root_user(self):
        """
        This enables login from any host for the root user and provides
        the user with a generated root password.
        """
        uri = "/instances/%s/root" % self.id
        resp, body = self.manager.api.method_post(uri)
        return body["user"]["password"]


    def root_user_status(self):
        uri = "/instances/%s/root" % self.id
        resp, body = self.manager.api.method_get(uri)
        return body["rootEnabled"]


    def restart(self):
        """Restarts this instance."""
        uri = "/instances/%s/action" % self.id
        body = {"restart": {}}
        self.manager.api.method_post(uri, body=body)


    def resize(self, flavor):
        """Set the size of this instance to a different flavor."""
        uri = "/instances/%s/action" % self.id
        # We need the flavorRef, not the flavor or size.
        flavorRef = self.manager.api._get_flavor_ref(flavor)
        body = {"resize": {"flavorRef": flavorRef}}
        self.manager.api.method_post(uri, body=body)


    def resize_volume(self, size):
        """Change the size of the volume for this instance."""
        curr_size = self.volume.get("size")
        if size <= curr_size:
            raise exc.InvalidVolumeResize("The new volume size must be larger than the current volume size of '%s'." % curr_size) 
        uri = "/instances/%s/action" % self.id
        body = {"resize": {"volume": {"size": size}}}
        self.manager.api.method_post(uri, body=body)


    def _get_flavor(self):
        try:
            ret = self._flavor
        except AttributeError:
            ret = self._flavor = CloudDatabaseFlavor(self.manager, {})
        return ret

    def _set_flavor(self, flavor):
        if isinstance(flavor, dict):
            self._flavor = CloudDatabaseFlavor(self.manager, flavor, True)
        else:
            # Must be an instance
            self._flavor = flavor

    flavor = property(_get_flavor, _set_flavor)


class CloudDatabaseDatabase(BaseResource):
    pass


class CloudDatabaseUser(BaseResource):
    pass


class CloudDatabaseFlavor(BaseResource):
    pass


class CloudDatabaseClient(BaseClient):
    def _configure_manager(self):
        self._manager = BaseManager(self, resource_class=CloudDatabaseInstance,
               response_key="instance", uri_base="instances")
        self._flavor_manager = BaseManager(self,
                resource_class=CloudDatabaseFlavor, response_key="flavor",
                uri_base="flavors")


    @assure_instance
    def list_databases(self, instance):
        return instance.list_databases()


    @assure_instance
    def create_database(self, instance, name, character_set=None,
            collate=None):
        """Creates a database with the specified name on the given instance."""
        return instance.create_database(name, character_set=character_set,
                collate=collate)


    @assure_instance
    def delete_database(self, instance, name):
        """Deletes the database by name on the given instance."""
        return instance.delete_database(name)


    @assure_instance
    def list_users(self, instance):
        return instance.list_users()


    @assure_instance
    def create_user(self, instance, name, password, database_names):
        """
        Creates a user with the specified name and password, and gives that
        user access to the spcified database(s).
        """
        return instance.create_user(name=name, password=password,
                database_names=database_names)


    @assure_instance
    def delete_user(self, instance, name):
        """Deletes the user by name on the given instance."""
        return instance.delete_user(name)


    @assure_instance
    def enable_root_user(self, instance):
        """
        This enables login from any host for the root user and provides
        the user with a generated root password.
        """
        return instance.enable_root_user()


    @assure_instance
    def root_user_status(self, instance):
        """Returns True if the given instance is root-enabled."""
        return instance.root_user_status()


    @assure_instance
    def resize(self, instance, flavor):
        """Set the size of the instance to a different flavor."""
        return instance.resize(flavor)


    def list_flavors(self):
        """Return a list of all available Flavors."""
        return self._flavor_manager.list()


    def get_flavor(self, flavor_id):
        """Returns a specific Flavor object by ID."""
        return self._flavor_manager.get(flavor_id)


    def _get_flavor_ref(self, flavor):
        flavor_obj = None
        if isinstance(flavor, CloudDatabaseFlavor):
            flavor_obj = flavor
        elif isinstance(flavor, int):
            # They passed an ID or a size
            try:
                flavor_obj = self.get_flavor(flavor)
            except exc.NotFound:
                # Must be either a size or bad ID, which will
                # be handled below
                pass
        if flavor_obj is None:
            # Try flavor name
            flavors = self.list_flavors()
            try:
                flavor_obj = [flav for flav in flavors
                        if flav.name == flavor][0]
            except IndexError:
                # No such name; try matching RAM
                try:
                    flavor_obj = [flav for flav in flavors
                            if flav.ram == flavor][0]
                except IndexError:
                   raise exc.FlavorNotFound("Could not determine flavor from '%s'." % flavor)
        # OK, we have a Flavor object. Get the href
        href = [link["href"] for link in flavor_obj.links
                if link["rel"] == "self"][0]
        return href


    def _create_body(self, name, flavor=None, volume=None, databases=None,
            users=None, character_set=None, collate=None, password=None,
            database_names=None):
        """
        Used to create the dict required to create any of the following:
            A database instance
            A database for an instance
            A user for an instance
        """
        if character_set is not None:
            # Creating a database
            body = {"databases": [
                    {"name": name,
                    "character_set": character_set,
                    "collate": collate,
                    }]}
        elif password is not None:
            # Creating a user
            db_dicts = [{"name": db} for db in database_names]
            body = {"users": [
                    {"name": name,
                    "password": password,
                    "databases": db_dicts,
                    }]}
        else:
            if flavor is None:
                flavor = 1
            flavor_ref = self._get_flavor_ref(flavor)
            if volume is None:
                volume = 1
            if databases is None:
                databases = []
            if users is None:
                users = []
            body = {"instance": {
                    "name": name,
                    "flavorRef": flavor_ref,
                    "volume": {"size": volume},
                    "databases": databases,
                    "users": users,
                    }}
        return body