#    Copyright 2011 Lockheed Martin

'''
Created on Mar 4, 2011

Base model class for learning registry data model

@author: jpoyau
'''
from pylons import config
from lr.lib import ModelParser, getFileString
import couchdb, os, logging, datetime, re, pprint, json 
from uuid import uuid4
from os import path

log = logging.getLogger(__name__)


        
#initialize the couchDB server
appConfig = config['app_conf']

#Default couchdb server that use by all the models when none is provided.
defaultCouchServer =  couchdb.Server(appConfig['couchdb.url'])    


class BaseModel(object):
    """Base model class for Learning Registry data models"""
    
    _ID = '_id'
    _REV = '_rev'
    _SPEC_DATA = '_specData'

    @staticmethod
    def createDB(name, server=defaultCouchServer):
        try:
            server.create(name)
        except Exception as ex:
            pass
            #log.exception(ex)
        return server[name]
                
    def __init__(self, data=None):
        
        # Use a static string for to set the spec data property to make easy to 
        # distinguish which attributes are from the spec from those that added
        # for class processing.
        self.__dict__[self._SPEC_DATA] = {}
        self.__dict__[self._ID] = None
        self.__dict__[self._REV] = None
        
        spec_data = data
        if data is not None:
            if isinstance(data, str) or isinstance(data, unicode):
                # Check to see if the data is a file path. if so load the the file
                if path.exists(data):
                    spec_data = json.loads(getFileString(data))
                else:
                    spec_data = json.loads(data)
            self.__setattr__(self._SPEC_DATA, spec_data)
            
    def __setattr__(self, name, value):
        # First check if the attribute that is getting set is an helper class attribute
        # outside of the spec data.  We determine this  by checking the self.__dict__ to
        # see if the attribute name is in there otherwise the attribute is treated has to be
        # spec data attribute.
        if name == self._SPEC_DATA:
            self.__dict__[self._SPEC_DATA] = value
        elif name in self._modelParser.modelInfo.keys():
            self._modelParser.validateField(name, value, self._specData)
            self.__dict__[self._SPEC_DATA][name] = value
        elif name in self.__dict__.keys():
            self.__dict__[name] = value
        else:
            raise AttributeError("'"+self.__class__.__name__+
                                             "' object has no attribute'"+name+"'")
    
    def __getattr__(self, name):
        # Check if the attribute name is a spec attribute.
        if name in self._modelParser.modelInfo.keys():
            # If it is a spec attribute  and  it is set in the _specData  
            # return it otherwise return None
            if name in self.__dict__[self._SPEC_DATA].keys():
                return self.__dict__[self._SPEC_DATA][name]
            else:
                return None
        elif name in self.__dict__.keys():
            return self.__dict__[name]
        else:
            raise AttributeError("'"+self.__class__.__name__+
                                            "' object has no attribute'"+name+"'")
    
    def _preValidation(self):
        pass
        
    def _validate(self):
        self._modelParser.validate(self._specData)
        
    def _postValidation(self):
        pass
        
    def toJSON(self):
        """Returns JSON object of the spec data"""
        return json.dumps(self._specData)
        
    def validate(self):
        self._preValidation()
        self._validate()
        self._postValidation()
        
    def save(self,  doc_id= None, db = None):
        
        # Make sure the spec data conforms to the spec before save it to the database
        self.validate()
        
        # Check if we need to genarate an id for the document if none is provided.
        if doc_id is None:
            doc_id = uuid4().hex
        
        # If no database is provided use the default one.
        if db == None:
            db = self._defaultDB
        
        result = {'OK':True}   
        
        # Use a temporary variable to hold the document the be save. The coudb
        # client code updates the dictionary with the id and revision.  We want to 
        # keep the specData clean and conforming the the spec all the time.
        document = {self._ID: doc_id}
        document.update(self._specData)
    
        try:
            db[doc_id] = document
            
            self.__dict__[self._ID]   = document[self._ID] 
            self.__dict__[self._REV] = document[self._REV]
            
        except Exception as e:
            result['OK'] = False
            result['ERROR'] = "CouchDB save error:  "+str(e)
            log.exception("\n"+pprint.pformat(result, indent=4)+"\n"+
                      pprint.pformat(document, indent=4)+"\n\n")
                      
        return result
     
def paseCommand(modelKlass):
    from optparse import OptionParser
    from os import path
    import os
    
    parser.add_option("-j", "--json", dest="json", action = "store_true", 
                      default=False,
                      help="Show a json representation of data model spec.")
                    
    parser.add_option("-v", "--validate", dest="source",
                      help="""Validates a JSON object against the spec data model
                            The source JSON object can be a file or a string 
                            representation of the JSON object.
                            """
                        )
                        
    if options.json == True:
        print modelKlass._modelParser.asJSON()
    
    if options.source is not None:
        sourceString = ''
        # Check to see if source is a file path by checking if the file exists.
        if path.exists(options.source):
            sourceString = getFileString(options.source)
        else:
            sourceString = options.source
            
        model = modelKlass(sourceString)
        model.validate()
        print("\n\n Object conforms to "+model.modelName+" model spec")
        
    if options.modelDestination is not None and options.specFile is not None:
        print("Spec file: "+options.specFile+"\n")
        print("Data Model spec Destination Dir: "+options.modelDestination+"\n")
        extractModelsFromSpec(options.specFile, options.modelDestination)        
        
        
    