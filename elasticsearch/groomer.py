# Copyright (C) 2018 BROADSoftware
#
# This file is part of EzCluster
#
# EzCluster is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# EzCluster is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with EzCluster.  If not, see <http://www.gnu.org/licenses/lgpl-3.0.html>.

import os
import copy
import yaml
from misc import ERROR,setDefaultInMap,lookupRepository,lookupHelper
from schema import schemaMerge


CLUSTER="cluster"
CONFIG="config"
ELASTICSEARCH="elasticsearch"
ELASTIC="elastic"
ROLE="role"
DATA="data"
NAME="name"
DISABLED="disabled"
VERSION="version"
ES_NODES="es_nodes"
ROLES="roles"
ESNODES="esNodes"
ES_CONFIG="es_config"
NODE_MASTER="node.master"
NODE_DATA="node.data"
VARS="vars"
ES_INSTANCE_NAME="es_instance_name"
_ELASTICSEARCH_="_elasticsearch_"
NODES="nodes"
GROUP_BY_NAME="groupByName"
REPOSITORIES="repositories"
ROLE_PATHS="rolePaths"
HELPERS="helpers"
FOLDER="folder"

NODES="nodes"
PLAYBOOK_VARS="playbook_vars"
ES_VERSION="es_version"
ES_MAJOR_VERSION="es_major_version"

def groom(plugin, model):
    
    setDefaultInMap(model[CLUSTER][ELASTICSEARCH], DISABLED, False)
    if model[CLUSTER][ELASTICSEARCH][DISABLED]:
        return False
    lookupRepository(model, ELASTICSEARCH)
    lookupHelper(model, ELASTICSEARCH)
    model[DATA][ROLE_PATHS].add(model[DATA][HELPERS][ELASTICSEARCH][FOLDER])
    f = os.path.join(plugin.path, "default.yml")
    if os.path.exists(f):
        base = yaml.load(open(f))
    else:
        base = {}
        
    model[DATA][ESNODES] = []        
    """ 
    For each es_node, will merge elasticsearch vars from:
    - Plugin default configuration file
    - global from cluster definition file
    - parent role
    - es_node """
    for role in model[CLUSTER][ROLES]:
        if ELASTICSEARCH in role and NODES in role[ELASTICSEARCH]:
            index = -1
            for esnode in role[ELASTICSEARCH][NODES]:
                index += 1
                mymap = copy.deepcopy(base)
                # Add repository info.  There is two reasons to use a package url:
                # - It will be faster if the repo is local
                # - Seems yum install is bugged on current role:  
                #     TASK [ansible-elasticsearch : RedHat - Install Elasticsearch] **************************************************************************************************
                #     fatal: [w2]: FAILED! => {"msg": "The conditional check 'redhat_elasticsearch_install_from_repo.rc == 0' failed. The error was: error while evaluating conditional (redhat_elasticsearch_install_from_repo.rc == 0): 'dict object' has no attribute 'rc'"}  
                mymap["es_custom_package_url"] = model[DATA][REPOSITORIES][ELASTICSEARCH]["elasticsearch_package_url"]
                mymap["es_use_repository"] = False
                # Add global value
                if ELASTICSEARCH in model[CLUSTER] and PLAYBOOK_VARS in model[CLUSTER][ELASTICSEARCH]:
                    if not isinstance(model[CLUSTER][ELASTICSEARCH][PLAYBOOK_VARS], dict):
                        ERROR("Invalid global '{}.{}' definition:  not a dictionary".format(ELASTICSEARCH, PLAYBOOK_VARS))
                    else:
                        mymap = schemaMerge(mymap, model[CLUSTER][ELASTICSEARCH][PLAYBOOK_VARS])
                # Add the role specific value
                if PLAYBOOK_VARS in role[ELASTICSEARCH]:
                    if not isinstance(role[ELASTICSEARCH][PLAYBOOK_VARS], dict):
                        ERROR("Invalid role definition ('{}'):  '{}.{}' is not a dictionary".format(role[NAME], ELASTICSEARCH,PLAYBOOK_VARS))
                    else:
                        mymap = schemaMerge(mymap, role[ELASTICSEARCH][PLAYBOOK_VARS])
                # And get the es_node specific value
                if not isinstance(esnode, dict):
                    ERROR("Invalid node definition in role '{}':  item#{} is not a dictionary".format(role[NAME], index))
                else:
                    mymap = schemaMerge(mymap, esnode)
                if not ES_CONFIG in mymap or not NODE_MASTER in mymap[ES_CONFIG]:
                    ERROR("Invalid es_node definition in role '{}, item#{}: es_config.'node.master' must be defined".format(role[NAME], index))
                if not ES_CONFIG in mymap or not NODE_DATA in mymap[ES_CONFIG]:
                    ERROR("Invalid es_node definition in role '{}, item#{}: es_config.'node.data' must be defined".format(role[NAME], index))
                if not ES_INSTANCE_NAME in mymap:
                    ERROR("Invalid es_node definition in role '{}, item#{}: es_instance_name must be defined".format(role[NAME], index))
                mymap[ES_VERSION] = model[DATA][REPOSITORIES][ELASTICSEARCH][VERSION]
                mymap[ES_MAJOR_VERSION] = mymap[ES_VERSION][:2] + "X"
                esn = {}
                esn[ROLE] = role[NAME]
                esn[VARS] = mymap
                model[DATA][ESNODES].append(esn)
    # We must arrange for master nodes to be deployed first.
    model[DATA][ESNODES].sort(key=keyFromEsNode, reverse=False)   
    # We need to define an ansible group "_elasticsearch_" hosting all nodes with elasticsearch installed
    elasticGroup = []
    for role in model[CLUSTER][ROLES]:
        if ELASTICSEARCH in role and NODES in role[ELASTICSEARCH]:
            for node in role[NODES]:
                elasticGroup.append(node[NAME])
    model[DATA][GROUP_BY_NAME][_ELASTICSEARCH_] = elasticGroup
    return True


def keyFromEsNode(esNode):
    return "0" if esNode[VARS][ES_CONFIG][NODE_MASTER] else "1"       
        
            
