import datetime
import logging
import re
import urllib
import urllib2
import uuid
from xml.dom import minidom

# Smartly import hashlib and fall back on md5
try:
    from hashlib import md5
except ImportError:
    from md5 import md5


def make_utf8(dictionary):
    """
    Encodes all Unicode strings in the dictionary to UTF-8. Converts
    all other objects to regular strings.
    
    Returns a copy of the dictionary, doesn't touch the original.
    """
    
    result = {}
    for (key, value) in dictionary.iteritems():
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        else:
            value = str(value)
        result[key] = value
    return result


class Configuration(object):
    """
    Stores the configuration elements required by the API.
    """

    def __init__(self, appid, secret, 
                 serviceurl, origin='rusticisoftware.pythonlibrary.2.0.0'):
        self.appid = appid
        self.secret = secret
        self.serviceurl = serviceurl
        self.origin = origin;

    def __repr__(self):
        return 'Configuration for AppID %s from origin %s' % (
               self.appid, self.origin)
        
class ScormCloudService(object):
    """
    Primary cloud service object that provides access to the more specific
    service areas, like the RegistrationService.
    """

    def __init__(self, configuration):
        self.config = configuration
        
    @classmethod
    def withconfig(cls, config):
        """
        Named constructor that creates a ScormCloudService with the specified
        Configuration object.

        Arguments:
        config -- the Configuration object holding the required configuration
            values for the SCORM Cloud API
        """
        return cls(config)

    @classmethod
    def withargs(cls, appid, secret, serviceurl, origin):
        """
        Named constructor that creates a ScormCloudService with the specified
        configuration values.

        Arguments:
        appid -- the AppID for the application defined in the SCORM Cloud
            account
        secret -- the secret key for the application
        serviceurl -- the service URL for the SCORM Cloud web service. For
            example, http://cloud.scorm.com/EngineWebServices
        origin -- the origin string for the application software using the
            API/Python client library
        """
        return cls(Configuration(appid, secret, serviceurl, origin))

    @property
    def course_service(self):
        return CourseService(self)

    def get_course_service(self):
        """
        Retrieves the CourseService.
        """
        return CourseService(self)

    @property
    def debug_service(self):
        return DebugService(self)

    def get_debug_service(self):
        """
        Retrieves the DebugService.
        """
        return DebugService(self)

    @property
    def registration_service(self):
        return RegistrationService(self)

    def get_registration_service(self):
        """
        Retrieves the RegistrationService.
        """
        return RegistrationService(self)

    @property
    def reporting_service(self):
        return ReportingService(self)

    def get_reporting_service(self):
        """
        Retrieves the ReportingService.
        """
        return ReportingService(self)

    @property
    def upload_service(self):
        return UploadService(self)
    
    def get_upload_service(self):
        """
        Retrieves the UploadService.
        """
        return UploadService(self)
    
    def request(self):
        """
        Convenience method to create a new ServiceRequest.
        """
        return ServiceRequest(self)

    def make_call(self, method, **kwargs):
        """
        Convenience method to create and call a ServiceRequest
        """
        return self.request().call_service(method, **kwargs)


class BaseServiceArea(object):
    def __init__(self, service):
        self.service = service

    @staticmethod
    def build_params(locals_received):
        """
        takes a dict and returns a new dict that excludes items where value is
        None or key == 'self'. It's especially useful to pass locals() to this.
        """
        return dict(((key, value) for key, value in locals_received.iteritems() if value is not None and key != 'self'))

    def build_and_make_call(self, method_name, locals_received):
        """
        Makes a call to the named method based on parameters from locals_received

        method_name -- name of the remote method to call
        locals_received -- dict of parameters, usually just locals(). values
            will be excluded if None or if key == 'self'
        """
        return self.service.make_call(method_name, **self.build_params(locals_received))
        

class DebugService(BaseServiceArea):
    """
    Debugging and testing service that allows you to check the status of the
    SCORM Cloud and test your configuration settings.
    """

    def ping(self):
        """
        A simple ping that checks the connection to the SCORM Cloud.
        """
        try:
            xmldoc = self.service.make_call('rustici.debug.ping')
            return xmldoc.documentElement.attributes['stat'].value == 'ok'
        except (ScormCloudError, IOError):
            return False
    
    def authping(self):
        """
        An authenticated ping that checks the connection to the SCORM Cloud
        and verifies the configured credentials.
        """
        try:
            xmldoc = self.service.make_call('rustici.debug.authPing')
            return xmldoc.documentElement.attributes['stat'].value == 'ok'
        except (ScormCloudError, IOError):
            return False


class UploadService(BaseServiceArea):
    """
    Service that provides functionality to upload files to the SCORM Cloud.
    """

    def get_upload_token(self):
        """
        Retrieves an upload token which must be used to successfully upload a
        file.
        """
        xmldoc = self.service.make_call('rustici.upload.getUploadToken')
        serverNodes = xmldoc.getElementsByTagName('server')
        tokenidNodes = xmldoc.getElementsByTagName('id')
        server = None
        for s in serverNodes:
            server = s.childNodes[0].nodeValue
        tokenid = None
        for t in tokenidNodes:
            tokenid = t.childNodes[0].nodeValue
        if server and tokenid:
            token = UploadToken(server,tokenid)
            return token

    def get_upload_url(self, callbackurl):
        """
        Returns a URL that can be used to upload a file via HTTP POST, through
        an HTML form element action, for example.
        """
        token = self.get_upload_token()
        if token:
            return '?'.join(self.service.request().build_url('rustici.upload.uploadFile', tokenid=token.tokenid, redirecturl=callbackurl))
        
    def delete_file(self, location):
        """
        Deletes the specified file.
        """
        locParts = location.split("/")
        return self.service.make_call('rustici.upload.deleteFiles', file=locParts[len(locParts) - 1])
        
    
class CourseService(BaseServiceArea):
    """
    Service that provides methods to manage and interact with courses on the
    SCORM Cloud. These methods correspond to the "rustici.course.*" web service
    methods.
    """

    def import_uploaded_course(self, courseid, path):
        """
        Imports a SCORM PIF (zip file) from an existing zip file on the SCORM
        Cloud server.

        Arguments:
        courseid -- the unique identifier for the course
        path -- the relative path to the zip file to import
        """
        result = self.build_and_make_call('rustici.course.importCourse', locals())
        ir = ImportResult.list_from_result(result)
        return ir
    
    def delete_course(self, courseid):
        """
        Deletes the specified course.

        Arguments:
        courseid -- the unique identifier for the course
        """
        return self.build_and_make_call('rustici.course.deleteCourse', locals())

    def get_assets(self, courseid, path=None):
        """
        Downloads a file from a course by path. If no path is provided, all the
        course files will be downloaded contained in a zip file.

        Arguments:
        courseid -- the unique identifier for the course
        path -- the path (relative to the course root) of the file to download.
            If not provided or is None, all course files will be downloaded.
        """
        return self.build_and_make_call('rustici.course.getAssets', locals())
        
    def get_course_list(self, courseIdFilterRegex=None):
        """
        Retrieves a list of CourseData elements for all courses owned by the
        configured AppID that meet the specified filter criteria.

        Arguments:
        courseIdFilterRegex -- (optional) Regular expression to filter courses
            by ID
        """
        result = self.build_and_make_call('rustici.course.getCourseList', {'filter' : courseIdFilerRegex})
        courses = CourseData.list_from_result(result)
        return courses 

    def get_preview_url(self, courseid, redirecturl, stylesheeturl=None):
        """
        Gets the URL that can be opened to preview the course without the need
        for a registration.

        Arguments:
        courseid -- the unique identifier for the course
        redirecturl -- the URL to which the browser should redirect upon course
            exit
        stylesheeturl -- the URL for the CSS stylesheet to include
        """
        params = self.build_params({
            'courseid' : courseid,
            'redirecturl' : redirecturl,
            'stylesheet' : stylesheeturl
        })
        url = '?'.join(self.service.request().build_url('rustici.course.preview', **params))
        logging.info('preview link: '+ url)
        return url

    def get_metadata(self, courseid):
        """
        Gets the course metadata in XML format.

        Arguments:
        courseid -- the unique identifier for the course
        """
        return self.build_and_make_call('rustici.course.getMetadata', locals())

    def get_property_editor_url(self, courseid, stylesheetUrl=None, 
                                notificationFrameUrl=None):
        """
        Gets the URL to view/edit the package properties for the course.
        Typically used within an IFRAME element.

        Arguments:
        courseid -- the unique identifier for the course
        stylesheeturl -- URL to a custom editor stylesheet
        notificationFrameUrl -- Tells the property editor to render a sub-iframe
            with this URL as the source. This can be used to simulate an 
            "onload" by using a notificationFrameUrl that is on the same domain 
            as the host system and calling parent.parent.method()
        """
        # this should go away if we can change method parameter names to match
        params = self.build_params({
            'courseid' : courseid,
            'stylesheet' : stylesheetUrl,
            'notificationframesrc' : notificationFrameUrl
        })

        url = '?'.join(self.service.request().build_url('rustici.course.properties', **params))

        logging.info('properties link: '+url)
        return url
    
    def get_attributes(self, courseid): 
        """
        Retrieves the list of associated attributes for the course. 

        Arguments:
        courseid -- the unique identifier for the course
        """
        xmldoc = self.build_and_make_call('rustici.course.getAttributes', locals())

        attrNodes = xmldoc.getElementsByTagName('attribute')
        atts = {}
        for an in attrNodes:
            atts[an.attributes['name'].value] = an.attributes['value'].value
        return atts
        
    def update_attributes(self, courseid, attributePairs):
        """
        Updates the specified attributes for the course.

        Arguments:
        courseid -- the unique identifier for the course
        attributePairs -- the attribute name/value pairs to update
        """
        xmldoc = self.service.make_call('rustici.course.updateAttributes', courseid=courseid, **attributePairs)

        attrNodes = xmldoc.getElementsByTagName('attribute')
        atts = {}
        for an in attrNodes:
            atts[an.attributes['name'].value] = an.attributes['value'].value
        return atts
        

class RegistrationService(BaseServiceArea):
    """
    Service that provides methods for managing and interacting with
    registrations on the SCORM Cloud. These methods correspond to the
    "rustici.registration.*" web service methods.
    """

    def create_registration(self, regid, courseid, userid, fname, lname, 
                            email=None):
        """
        Creates a new registration (an instance of a user taking a course).

        Arguments:
        regid -- the unique identifier for the registration
        courseid -- the unique identifier for the course
        userid -- the unique identifier for the learner
        fname -- the learner's first name
        lname -- the learner's last name
        email -- the learner's email address
        """
        if regid is None:
            regid = str(uuid.uuid1())
        xmldoc = self.build_and_make_call('rustici.registration.createRegistration', locals())
        successNodes = xmldoc.getElementsByTagName('success')
        if successNodes.length == 0:
            raise ScormCloudError("Create Registration failed.  " + 
                                  xmldoc.err.attributes['msg'])
        return regid
        
    def get_launch_url(self, regid, redirecturl, cssUrl=None, courseTags=None, 
                       learnerTags=None, registrationTags=None):
        """
        Gets the URL to directly launch the course in a web browser.
        
        Arguments:
        regid -- the unique identifier for the registration
        redirecturl -- the URL to which the SCORM player will redirect upon
            course exit
        cssUrl -- the URL to a custom stylesheet
        courseTags -- comma-delimited list of tags to associate with the
            launched course
        learnerTags -- comma-delimited list of tags to associate with the
            learner launching the course
        registrationTags -- comma-delimited list of tags to associate with the
            launched registration
        """
        redirecturl = redirecturl + '?regid=' + regid

        return '?'.join(self.service.request().build_url(
            'rustici.registration.launch', **self.build_params(locals())))

    
    def get_registration_list(self, regIdFilterRegex=None, 
                              courseIdFilterRegex=None):
        """
        Retrieves a list of registration associated with the configured AppID.
        Can optionally be filtered by registration or course ID.

        Arguments:
        regIdFilterRegex -- (optional) the regular expression used to filter the 
            list by registration ID
        courseIdFilterRegex -- (optional) the regular expression used to filter
            the list by course ID
        """
        result = self.build_and_make_call(
            'rustici.registration.getRegistrationList', locals())
        regs = RegistrationData.list_from_result(result)
        return regs 
        
    def get_registration_result(self, regid, resultsformat):
        """
        Gets information about the specified registration.

        Arguments:
        regid -- the unique identifier for the registration
        resultsformat -- (optional) can be "course", "activity", or "full" to
            determine the level of detail returned. The default is "course"
        """
        return self.build_and_make_call(
            'rustici.registration.getRegistrationResult', locals())

    def get_launch_history(self, regid):
        """
        Retrieves a list of LaunchInfo objects describing each launch. These
        LaunchInfo objects do not contain the full launch history log; use
        get_launch_info to retrieve the full launch information.

        Arguments:
        regid -- the unique identifier for the registration
        """
        return self.build_and_make_call('rustici.registration.getLaunchHistory', locals())
        
    def reset_registration(self, regid):
        """
        Resets all status data for the specified registration, essentially
        restarting the course for the associated learner.

        Arguments:
        regid -- the unique identifier for the registration
        """
        return self.build_and_make_call('rustici.registration.resetRegistration', locals())
        
    def reset_global_objectives(self, regid):
        """
        Clears global objective data for the specified registration.

        Arguments:
        regid -- the unique identifier for the registration
        """
        return self.build_and_make_call(
               'rustici.registration.resetGlobalObjectives', locals())
        
    def delete_registration(self, regid):
        """
        Deletes the specified registration.

        Arguments:
        regid -- the unique identifier for the registration
        """
        return self.build_and_make_call('rustici.registration.deleteRegistration', locals())
        

class ReportingService(BaseServiceArea):
    """
    Service that provides methods for interacting with the Reportage service.
    """

    def get_reportage_date(self):
        """
        Gets the date/time, according to Reportage.
        """
        reportUrl = (self._get_reportage_service_url() + 
                    'Reportage/scormreports/api/getReportDate.php?appId=' + 
                    self.service.config.appid)
        cloudsocket = urllib2.urlopen(reportUrl,None)
        reply = cloudsocket.read()
        cloudsocket.close()
        return datetime.datetime.strptime(reply,"%Y-%m-%d %H:%M:%S")
        
    def get_reportage_auth(self, navperm, allowadmin):
        """
        Authenticates against the Reportage application, returning a session
        string used to make subsequent calls to launchReport.

        Arguments:
        navperm -- the Reportage navigation permissions to assign to the
            session. If "NONAV", the session will be prevented from navigating
            away from the original report/widget. "DOWNONLY" allows the user to
            drill down into additional detail. "FREENAV" allows the user full
            navigation privileges and the ability to change any reporting
            parameter.
        allowadmin -- if True, the Reportage session will have admin privileges
        """
        params = {
            'navpermission' : navperm,
            'admin' : 'true' if allowadmin is True else 'false'
        }
        xmldoc = self.build_and_make_call('rustici.reporting.getReportageAuth', params)
        token = xmldoc.getElementsByTagName('auth')
        if token.length > 0:
            return token[0].childNodes[0].nodeValue
        
    def _get_reportage_service_url(self):
        """
        Returns the base Reportage URL.
        """
        return self.service.config.serviceurl.replace('EngineWebServices','')

    def _get_base_reportage_url(self):
        return (self._get_reportage_service_url() + 'Reportage/reportage.php' +
               '?appId=' + self.service.config.appid)
        
    def get_report_url(self, auth, reportUrl):
        """
        Returns an authenticated URL that can launch a Reportage session at
        the specified Reportage entry point.

        Arguments:
        auth -- the Reportage authentication string, as retrieved from
            get_reportage_auth
        reportUrl -- the URL to the desired Reportage entry point
        """
        return '?'.join(self.service.request().build_url(
            'rustici.reporting.launchReport', **self.build_params(locals())))

    def get_reportage_url(self, auth):
        """
        Returns the authenticated URL to the main Reportage entry point.

        Arguments:
        auth -- the Reportage authentication string, as retrieved from
            get_reportage_auth
        """
        reporturl = self._get_base_reportage_url()
        return self.get_report_url(auth, reporturl)
    
    def get_course_reportage_url(self, auth, courseid):
        reporturl = self._get_base_reportage_url() + '&courseid=' + courseid
        return self.get_report_url(auth, reporturl)
         
    def get_widget_url(self, auth, widgettype, widgetSettings):
        """
        Gets the URL to a specific Reportage widget, using the provided
        widget settings.

        Arguments:
        auth -- the Reportage authentication string, as retrieved from
            get_reportage_auth
        widgettype -- the widget type desired (for example, learnerSummary)
        widgetSettings -- the WidgetSettings object for the widget type
        """
        reportUrl = (self._get_reportage_service_url() + 
                    'Reportage/scormreports/widgets/')
        widgetUrlTypeLib = {
            'allSummary':'summary/SummaryWidget.php?srt=allLearnersAllCourses',
            'courseSummary':'summary/SummaryWidget.php?srt=singleCourse',
            'learnerSummary':'summary/SummaryWidget.php?srt=singleLearner',
            'learnerCourse':'summary/SummaryWidget.php?srt='
                            'singleLearnerSingleCourse',
            'courseActivities':'DetailsWidget.php?drt=courseActivities',
            'learnerRegistration':'DetailsWidget.php?drt=learnerRegistration',
            'courseComments':'DetailsWidget.php?drt=courseComments',
            'learnerComments':'DetailsWidget.php?drt=learnerComments',
            'courseInteractions':'DetailsWidget.php?drt=courseInteractions',
            'learnerInteractions':'DetailsWidget.php?drt=learnerInteractions',
            'learnerActivities':'DetailsWidget.php?drt=learnerActivities',
            'courseRegistration':'DetailsWidget.php?drt=courseRegistration',
            'learnerRegistration':'DetailsWidget.php?drt=learnerRegistration',
            'learnerCourseActivities':'DetailsWidget.php?drt='
                                      'learnerCourseActivities',
            'learnerTranscript':'DetailsWidget.php?drt=learnerTranscript',
            'learnerCourseInteractions':'DetailsWidget.php?drt='
                                        'learnerCourseInteractions',
            'learnerCourseComments':'DetailsWidget.php?drt='
                                    'learnerCourseComments',
            'allLearners':'ViewAllDetailsWidget.php?viewall=learners',
            'allCourses':'ViewAllDetailsWidget.php?viewall=courses'}
        reportUrl += widgetUrlTypeLib[widgettype]
        reportUrl += '&appId='+self.service.config.appid
        reportUrl += widgetSettings.get_url_encoding()
        reportUrl = self.get_report_url(auth, reportUrl)
        return reportUrl
        

class WidgetSettings(object):
    def __init__(self, dateRangeSettings, tagSettings):
        self.dateRangeSettings = dateRangeSettings
        self.tagSettings = tagSettings
        
        self.courseId = None
        self.learnerId = None
        
        self.showTitle = True;
        self.vertical = False;
        self.public = True;
        self.standalone = True;
        self.iframe = False;
        self.expand = True;
        self.scriptBased = True;
        self.divname = '';
        self.embedded = True;
        self.viewall = True;
        self.export = True;
        
        
    def get_url_encoding(self):
        """
        Returns the widget settings as encoded URL parameters to add to a 
        Reportage widget URL.
        """
        widgetUrlStr = '';
        if self.courseId is not None:
            widgetUrlStr += '&courseId=' + self.courseId
        if self.learnerId is not None:
            widgetUrlStr += '&learnerId=' + self.learnerId
        
        widgetUrlStr += '&showTitle=' + 'self.showTitle'.lower()
        widgetUrlStr += '&standalone=' + 'self.standalone'.lower()
        if self.iframe:
            widgetUrlStr += '&iframe=true'
        widgetUrlStr += '&expand=' + 'self.expand'.lower()
        widgetUrlStr += '&scriptBased=' + 'self.scriptBased'.lower()
        widgetUrlStr += '&divname=' + self.divname
        widgetUrlStr += '&vertical=' + 'self.vertical'.lower()
        widgetUrlStr += '&embedded=' + 'self.embedded'.lower()

        if self.dateRangeSettings is not None:
            widgetUrlStr += self.dateRangeSettings.get_url_encoding()

        if self.tagSettings is not None:
            widgetUrlStr += self.tagSettings.get_url_encoding()
        
        return widgetUrlStr

    
class DateRangeSettings(object):
    def __init__(self, dateRangeType, dateRangeStart, 
                 dateRangeEnd, dateCriteria):
        self.dateRangeType=dateRangeType
        self.dateRangeStart=dateRangeStart
        self.dateRangeEnd=dateRangeEnd        
        self.dateCriteria=dateCriteria
        
    def get_url_encoding(self):
        """
        Returns the DateRangeSettings as encoded URL parameters to add to a
        Reportage widget URL.
        """
        dateRangeStr = ''
        if self.dateRangeType == 'selection':
            dateRangeStr +='&dateRangeType=c'
            dateRangeStr +='&dateRangeStart=' + self.dateRangeStart
            dateRangeStr +='&dateRangeEnd=' + self.dateRangeEnd
        else:
            dateRangeStr +='&dateRangeType=' + self.dateRangeType
        
        dateRangeStr += '&dateCriteria=' + self.dateCriteria
        return dateRangeStr
        
class TagSettings(object):
    def __init__(self):
        self.tags = {'course':[],'learner':[],'registration':[]}
    
    def add(self, tagType, tagValue):
        self.tags[tagType].append(tagValue)
        
    def get_tag_str(self, tagType):
        return ','.join(set(self.tags[tagType])) + "|_all"

    def get_view_tag_str(self, tagType):
        return ','.join(set(self.tags[tagType]))
        
    def get_url_encoding(self):
        tagUrlStr = ''
        for k in self.tags.keys():
            if len(set(self.tags[k])) > 0:
                tagUrlStr += '&' + k + 'Tags=' + self.get_tag_str(k)
                tagUrlStr += ('&view' + k.capitalize() + 'TagGroups=' + 
                             self.get_view_tag_str(k))
        return tagUrlStr
    
    
class ScormCloudError(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return repr(self.msg)

class ImportResult(object):
    def __init__(self, importResultElement):
        self.wasSuccessful = False
        self.title = ""
        self.message = ""
        self.parserWarnings = []
        if importResultElement is not None:
            self.wasSuccessful = (importResultElement.attributes['successful']
                                 .value == 'true')
            self.title = (importResultElement.getElementsByTagName("title")[0]
                         .childNodes[0].nodeValue)
            self.message = (importResultElement
                           .getElementsByTagName("message")[0]
                           .childNodes[0].nodeValue)
            xmlpw = importResultElement.getElementsByTagName("warning")
            for pw in xmlpw:
                self.parserWarnings.append(pw.childNodes[0].nodeValue)

    @classmethod
    def list_from_result(cls, xmldoc):
        """
        Returns a list of ImportResult objects by parsing the raw result of an
        API method that returns importresult elements.

        Arguments:
        xmldoc -- the minidom.Document instance resulting from a remote call
        """
        importresults = xmldoc.getElementsByTagName("importresult")
        return [cls(ir) for ir in importresults]

class CourseData(object):
    courseId = ""
    numberOfVersions = 1
    numberOfRegistrations = 0
    title = ""

    def __init__(self, courseDataElement):
        if courseDataElement is not None:
            self.courseId = courseDataElement.attributes['id'].value
            self.numberOfVersions = (courseDataElement.attributes['versions']
                                    .value)
            self.numberOfRegistrations = (courseDataElement
                                        .attributes['registrations'].value)
            self.title = courseDataElement.attributes['title'].value;

    @classmethod
    def list_from_result(cls, xmldoc):
        """
        Returns a list of CourseData objects by parsing the raw result of an
        API method that returns course elements.

        Arguments:
        data -- the raw result of the API method
        """
        allResults = [];
        courses = xmldoc.getElementsByTagName("course")
        for course in courses:
            allResults.append(cls(course))
        return allResults

class UploadToken(object):
    server = ""
    tokenid = ""
    def __init__(self, server, tokenid):
        self.server = server
        self.tokenid = tokenid

class RegistrationData(object):
    courseId = ""
    registrationId = ""

    def __init__(self, regDataElement):
        if regDataElement is not None:
            self.courseId = regDataElement.attributes['courseid'].value
            self.registrationId = regDataElement.attributes['id'].value

    @classmethod
    def list_from_result(cls, xmldoc):
        """
        Returns a list of RegistrationData objects by parsing the result of an
        API method that returns registration elements.

        Arguments:
        data -- the raw result of the API method
        """
        regs = xmldoc.getElementsByTagName("registration")
        return [cls(reg) for reg in regs]


class ServiceRequest(object):
    """
    Helper object that handles the details of web service URLs and parameter
    encoding and signing. Set the web service method parameters on the 
    parameters attribute of the ServiceRequest object and then call
    call_service with the method name to make a service request.
    """
    def __init__(self, service):
        self.service = service
        self.parameters = dict()
        self.file_ = None

    def call_service(self, method, **kwargs):
        """
        Calls the specified web service method using any parameters set on the
        ServiceRequest.

        Arguments:
        method -- the full name of the web service method to call.
            For example: rustici.registration.createRegistration
        **kwargs -- parameters to pass to the remote method. These will override
            self.parameters
        """
        url, encoded_params = self.build_url(method, **kwargs)

        #if self.file_ is not None:
            # TODO: Implement file upload
        rawresponse = self.send_post(url, encoded_params)
        response = self.get_xml(rawresponse)
        return response

    def build_url(self, method, **kwargs):
        """
        Build the components of a URL.

        method -- name of the remote method to call
        **kwargs -- any additional named parameters to pass to the remote method

        Returns a tuple of the base url, followed by the encoded parameters.
        Joining them with a '?' will get you the full URL.
        """
        request_params = {'method' : method}
        request_params.update(self.parameters)
        request_params.update(kwargs)
        request_params.update(self.auth_dict)
        encoded_params = self._encode_and_sign(request_params, self.service.config.secret)

        url = ScormCloudUtilities.clean_cloud_host_url(self.service.config.serviceurl)

        return url, encoded_params

    @staticmethod
    def get_xml(raw):
        """
        Parses the raw response string as XML and asserts that there was no
        error in the result.

        Arguments:
        raw -- the raw response string from an API method call
        """
        xmldoc = minidom.parseString(raw)
        rsp = xmldoc.documentElement
        if rsp.attributes['stat'].value != 'ok':
            err = rsp.firstChild
            raise ScormCloudError('SCORM Cloud Error: %s - %s' %
                            (err.attributes['code'].value, 
                             err.attributes['msg'].value))
        return xmldoc

    @staticmethod
    def send_post(url, postparams):
        cloudsocket = urllib2.urlopen(url, postparams)
        reply = cloudsocket.read()
        cloudsocket.close()
        return reply

    @staticmethod
    def _encode_and_sign(params, secret):
        """
        URL encodes the data in the dictionary, and signs it using the
        given secret, if a secret was given.

        Arguments:
        params -- the dictionary containing all key/value parameter pairs
        """ 

        params = make_utf8(params)
        signing = ''.join([key + params[key] for key in sorted(params.keys())])
        params['sig'] = md5(secret + signing).hexdigest()
        return urllib.urlencode(params)

    @property
    def auth_dict(self):
        """Return a dict of the 4 auth params that are required for each call"""
        return {
            'appid' : self.service.config.appid,
            'origin' : self.service.config.origin,
            'ts' : datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S"),
            'applib' : 'python'
        }


class ScormCloudUtilities(object):
    """
    Provides utility functions for working with the SCORM Cloud.
    """

    @staticmethod
    def get_canonical_origin_string(organization, application, version):
        """
        Helper function to build a proper origin string to provide to the
        SCORM Cloud configuration. Takes the organization name, application
        name, and application version.

        Arguments:
        organization -- the name of the organization that created the software
            using the Python Cloud library
        application -- the name of the application software using the Python
            Cloud library
        version -- the version string for the application software
        """
        namepattern = re.compile(r'[^a-z0-9]')
        versionpattern = re.compile(r'[^a-z0-9\.\-]')
        org = namepattern.sub('', organization.lower())
        app = namepattern.sub('', application.lower())
        ver = versionpattern.sub('', version.lower())
        return "%s.%s.%s" % (org, app, ver)

    @staticmethod
    def clean_cloud_host_url(url):
        """
        Simple function that helps ensure a working API URL. Assumes that the
        URL of the host service ends with /api and processes the given URL to
        meet this assumption.

        Arguments:
        url -- the URL for the Cloud service, typically as entered by a user
            in their configuration
        """
        parts = url.split('/')
        if not parts[len(parts) - 1] == 'api':
            parts.append('api')
        return '/'.join(parts)

