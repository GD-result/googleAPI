'''
Created on 02.03.2012

@author: ninja
'''
import gdata.apps.groups.service
import gdata.apps.groups.client
import gdata.apps.service
import gdata.auth
import pickle
import xmlrpclib

from config import SPACE
from config import TOP_PAGE
from config import WIKI_USER
from config import WIKI_PASS

class _GoogleApps():
    wiki_server = xmlrpclib.ServerProxy('https://wiki.griddynamics.net/rpc/xmlrpc');
    token_from_wiki = wiki_server.confluence1.login(WIKI_USER, WIKI_PASS);  
    token = "";
    domain = ""
    consumerKey = "";
    consumerSecret = "";  

    def request(self,content,NamePage,token,server,table_headers,flagNewPage):        
        pageExist = False;
        try:
            page = server.confluence1.getPage(token, SPACE, NamePage);
            if (flagNewPage):
                server.confluence1.removePage(token, page["id"])
            pageExist = True
        except:
            pass   
        if (flagNewPage) or (pageExist == False):
            parent = server.confluence1.getPage(token, SPACE, TOP_PAGE);
            page={
                  'parentId': parent['id'],
                  'space': SPACE,
                  'title': NamePage,
                  'content': table_headers + content #content
                  }
            server.confluence1.storePage(token, page);
        else:
            page['content'] += content;
            server.confluence1.updatePage(token, page,{'versionComment':'','minorEdit':1});
        pageTmp = server.confluence1.getPage(token, SPACE, NamePage);
        return pageTmp['id']
                   
        
    
    
    def LoadTokenFromFile(self,fileName):
        oauthToken = "";
        try:
            oauthfile = open(fileName, 'rb')
            self.domain = oauthfile.readline()[0:-1]
            oauthToken = pickle.load(oauthfile)
            self.consumerKey = oauthToken.oauth_input_params._consumer.key
            self.consumerSecret = oauthToken.oauth_input_params._consumer.secret
            oauthfile.close()
        except:
            oauthToken = "fileError"
        return oauthToken;    
    
    def __init__(self, fileName = "oauth.txt"):
        self.token = self.LoadTokenFromFile(fileName)
            
    def OAuthConnect(self,googleObj,consumerKey,consumerSecret):
        if self.token != "fileError":
            googleObj.domain = self.domain;
            googleObj.SetOAuthInputParameters(gdata.auth.OAuthSignatureMethod.HMAC_SHA1,consumerKey,consumerSecret)
            googleObj.SetOAuthToken(self.token)
            return googleObj;
        else:
            return self.token;  
               
    def Auth(self):
        self.groupClient = gdata.apps.groups.client.GroupsProvisioningClient(domain=self.domain)
        self.groupClient.ClientLogin(email=self.email, password=self.password, source ='apps')
        #access_token = gdata.gauth.ClientLoginToken(token);
        #self.groupClient = gdata.apps.groups.client.GroupsProvisioningClient(domain=self.domain, auth_token = access_token)
       
    def PrintGroupDetails(self,groupsEntry):
        print 'Group ID: ' + groupsEntry.group_id
        print 'Group Name: ' + groupsEntry.group_name
        print 'Description: ' + groupsEntry.description
        print 'Email Permissions: ' + groupsEntry.email_permission
        print ''
    
    def PrintMemberDetails(self,memberEntry):
        print 'Member ID: ' + memberEntry.member_id
        print 'Member Type: ' + memberEntry.member_type
        print 'Is Direct Member: ' + memberEntry.direct_member
        print ''
        
    def UsersInGroups(self,group_filter = domain):
        pageTitle = "";   
        pageName = "";
        pageMembers = " ";
        pageEmails = " ";
        pageExternalMembers = " ";
        pageSubgroups = " "
        pageDescription = " ";
        pageEmailPermissions = " "
        try:
            groupsObj = membersObj = self.OAuthConnect(gdata.apps.groups.service.GroupsService(), self.consumerKey, self.consumerSecret);
            if (membersObj == "fileError"):
                return -1;
            allUsersObj = self.OAuthConnect(gdata.apps.service.AppsService(), self.consumerKey, self.consumerSecret);
            allUsersInDomain = allUsersObj.RetrieveAllUsers()
            allGroups = groupsObj.RetrieveAllGroups();
        except gdata.apps.service.AppsForYourDomainException, exception:
            print exception['status'] # exception.error_code
            return -1;  
        for group in allGroups:
            pageTitle = group['groupId'];
            allMembersInGroup = membersObj.RetrieveAllMembers(group['groupId'],False);
            allMembersInGroup = sorted(allMembersInGroup, key=lambda k: k['memberId'].lower()) 
            pageName = group['groupId'].split("@")[0] + " mailing list"; 
            pageEmails = " ";
            pageMembers = " ";
            if (group['description'] != None):
                pageDescription = group['description'];
            else:
                pageDescription = " ";
            pageEmailPermissions = group['emailPermission']; 
            for member in allMembersInGroup:
                if member['memberId'] != '*':
                    for allUsersEntry in allUsersInDomain.entry:
                        if (allUsersEntry.title.text.encode('UTF-8') == member['memberId'].split("@")[0]):
                            if (allUsersEntry.login.suspended == "true"):
                                if member['memberId'].count(group_filter) != 0: 
                                    pageEmails = pageEmails + self.suspended("{color:red}", member['memberId'], "{color}") + ", ";
                                    pageMembers = pageMembers + self.suspended("{color:red}", member['memberId'].split("@")[0], "{color}") + ", ";
                                else:
                                    pageExternalMembers = pageExternalMembers + self.suspended("{color:red}", member['memberId'], "{color}") + ", ";
                            else:
                                if member['memberId'].count(group_filter) != 0: 
                                    pageEmails = pageEmails + member['memberId'] + ", ";
                                    pageMembers = pageMembers + self.suspended("[~", member['memberId'].split("@")[0], "]") + ", ";
                                else:
                                    pageExternalMembers = self.suspended("[~", pageExternalMembers + member['memberId'], "]") + ", ";
                            break;
            if (len(pageEmails) > 2): 
                pageEmails = pageEmails[:-2]
                pageMembers = pageMembers[:-2];       
            if (len(pageExternalMembers) > 2):
                pageExternalMembers = pageExternalMembers[:-2]         
            table_headers = "h1." + pageTitle + "\n ||Members ||Emails ||ExternalMembers ||Subgroups ||Description ||EmailPermissions ||\n";
            pageId = self.request("|" + pageMembers + "|" + pageEmails + "|" + pageExternalMembers + "|" \
                    + pageSubgroups + "|" + pageDescription + "|" + pageEmailPermissions +"|\n", pageName, 
                    self.token_from_wiki, self.wiki_server,table_headers,True);
            labelName = self.findSimbols(group['groupId'].split("@")[0])
            self.wiki_server.confluence1.addLabelByName(self.token_from_wiki, labelName, pageId);
        return 0;
    

    def GroupsWithMember(self):
        content = "";
        pageMembersOfGroups = " ";
        pageUserName = " "
        pageTitle = "Grid Dynamics mail users in Gmail."
        pageName = "Gmail-Users"
        table_headers = "h1." + pageTitle + "\n ||User ||Member of groups ||\n"
        try:
            membersObj = self.OAuthConnect(gdata.apps.service.AppsService(), self.consumerKey, self.consumerSecret)
            if (membersObj == "fileError"):
                return -1;
            groupObj = self.OAuthConnect(gdata.apps.groups.service.GroupsService(), self.consumerKey, self.consumerSecret);
            allMembers = membersObj.RetrieveAllUsers();
        except gdata.apps.service.AppsForYourDomainException, exception:
            print exception['status'] # exception.error_code
            return -1;
        sortedMasMembers = [];
        for memberEntry in allMembers.entry:
            sortedMasMembers.append([memberEntry.title.text.encode('UTF-8'),memberEntry.login.suspended])  
        sortedMasMembers.sort(key = self.SortByAlphabet) 
        flagNewPage = True;
        for i in range(len(sortedMasMembers)):
            allGroups = groupObj.RetrieveGroups(sortedMasMembers[i][0], True);
            pageMembersOfGroups = " ";
            for group in allGroups:
                pageMembersOfGroups = pageMembersOfGroups + group['groupId'] + ", ";
            if (len(pageMembersOfGroups) > 2):
                pageMembersOfGroups = pageMembersOfGroups[:-2]
            if (sortedMasMembers[i][1] == "true"):
                pageUserName = self.suspended("{color:red}", sortedMasMembers[i][0], "{color}");
            else:
                pageUserName = self.suspended("[~", sortedMasMembers[i][0], "]"); 
            content += "|" + pageUserName + "|" + pageMembersOfGroups + "| \n";      
        pageId = self.request(content, pageName, self.token_from_wiki, self.wiki_server,table_headers,flagNewPage);
        self.wiki_server.confluence1.addLabelByName(self.token_from_wiki, pageName, pageId);
        flagNewPage = False;
        return 0;
            
            
    def suspended(self,beginStr,userName,endStr):
        return beginStr + userName + endStr;
    

    def findSimbols(self,stringName):
        chars = ['!', '#', '&', '(', ')', '*', ',', '.', ':', ';', '<', '>', '?', '@', '[', ']', '^'];
        i = 0;
        while (i < len(chars)):
            k = 0;            
            while k <= len(stringName):
                number = stringName.find(chars[i]);  
                if (number == -1):
                    break;
                else:
                    strTmp = stringName[:number];
                    strTmp += '_';
                    strTmp += stringName[number+1:];
                    stringName = strTmp
                k += 1;
            i += 1;
        return stringName;
    
    def SortByAlphabet(self, inputStr):
        return inputStr[0][0].lower()
    
    
google = _GoogleApps() 
google.UsersInGroups()
google.GroupsWithMember();
