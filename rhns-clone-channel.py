#!/usr/bin/python

#quick script to demonstrate the main logic before the final script

### warning experimental script ###

##### EDIT THOSE VALUES FOLLOWING YOUR NEEDS #####
SATELLITE="rhns56-6.gsslab.fab.redhat.com"
USER="satadmin"
PWD="redhat"
#channel to copy from, label only
SOURCE="epel-6-64-ws"
#details of the channel to create that aren't read from the parent, do not change the name of the variables.
#all variables need to be set except parentLabel that should be set to "" for channels that don't have a parent
DESTINATION={ 'name' : "magix epel 6 ws", 'label' : "magix-epel-ws", 'parentLabel' : "magix-6-ws", 'summary' : "Clone of EPEL for RHEL6.4 64bits WS" }
import datetime
#dates to and from, using datetime.date(YYYY,MM,DD)
FROM_DATE=datetime.date(2001,01,01) # first january 2001
TO_DATE=datetime.date(2013,02,21) #release of rhel 6.4
DEBUG=5
##### DO NOT EDIT PAST THIS ######

#auth part
url = "https://%s/rpc/api" % (SATELLITE)
import xmlrpclib
client = xmlrpclib.Server(url)
key = client.auth.login(USER,PWD)
del PWD # we don't need that anyore

#read details
existingchannels = dict()
orig_details = client.channel.software.getDetails(key,SOURCE)

#create the destination if required
for channel in client.channel.listSoftwareChannels(key):
    existingchannels[channel['label']]=channel
#minimal version of this test
if orig_details['arch_name'] == 'x86_64':
    DESTINATION['archLabel'] = 'channel-x86_64'
elif orig_details['arch_name'] == 'IA-32':
    DESTINATION['archLabel'] = 'channel-ia32'
elif orig_details['arch_name'] == 'IA-64':
    DESTINATION['archLabel'] = 'channel-ia64'
else:
    print "unknown arch %s" % (orig_details['arch_name'])
DESTINATION['checksumType'] = orig_details['checksum_label']
if not DESTINATION['label'] in existingchannels.keys():
    new_channel = True
    client.channel.software.create(key,DESTINATION['label'],DESTINATION['name'],DESTINATION['summary'],DESTINATION['archLabel'], DESTINATION['parentLabel'],DESTINATION['checksumType'])
else:
    new_channel = False

#build the lists of content to push
#may fail on excevely large channels. avoid using on RHEL5 base channel.
package_list = list()
for package in client.channel.software.listAllPackages(key,SOURCE, FROM_DATE.isoformat(), TO_DATE.isoformat()) :
    package_list.append(package['id'])
errata_list = client.channel.software.listErrata(key,SOURCE,FROM_DATE.isoformat(), TO_DATE.isoformat())

if len(errata_list) > 0 :
    print "%d erratas selected" % (len(errata_list))
    passes = len(errata_list) / 50
    last_pass = False
    if len(errata_list) % 50 > 0 :
        passes = passes + 1
        last_pass = True
    erratas_to_push = list()
    erratas_pushed = 0
    current_pass = 1
    for errata in errata_list:
        erratas_to_push.append(errata['advisory_name'])
        print '\r'+"%d erratas prepared out of %d (pass %d of %d)%s" % (len(erratas_to_push),len(errata_list),current_pass,passes,"                     "),
        if len(erratas_to_push) == 50:
            if DEBUG >= 3:
                print "" # new line not to overwrite the previous one
                print "%d erratas to push in pass %d:" % (len(erratas_to_push),current_pass)
                if DEBUG >=4:
                    for errata in erratas_to_push:
                        print " - %s" % (errata)
            result = client.channel.software.mergeErrata(key,SOURCE,DESTINATION['label'],erratas_to_push)
            erratas_pushed = erratas_pushed + len(result)
            print '\r'+"%d erratas pushed out of %d (pass %d of %d)%s" % (erratas_pushed,len(errata_list),current_pass,passes,"                   "),
            if DEBUG >= 4:
                print "" # new line not to overwrite the previous one
                for errata in result:
                    print " - %s" % (errata['advisory_name'])
            current_pass = current_pass + 1
            erratas_to_push = list()
    if last_pass == True:
        if DEBUG >= 3:
            print "" # new line not to overwrite the previous one
            print "%d erratas to push in pass %d:" % (len(erratas_to_push),current_pass)
            if DEBUG >= 4:
                for errata in erratas_to_push:
                    print " - %s" % (errata)
        result = client.channel.software.mergeErrata(key,SOURCE,DESTINATION['label'],erratas_to_push)
        erratas_pushed = erratas_pushed + len(result)
        print '\r'+"%d erratas pushed out of %d (pass %d of %d)%s" % (erratas_pushed,len(errata_list),current_pass,passes, "                    "),
        if DEBUG >= 4:
            print "" # new line not to overwrite the previous one
            for errata in result:
                print " - %s" % (errata['advisory_name'])
    print "" #avoid writing next line to the same line
else:
    print "no errata selected"

#copy packages & erratas per group of 100
if not new_channel or len(errata_list) > 0:
    #compare content to revise the list of packages to upload, especially if this is not a new channel or erratas were merged.
    packages_in_destination = list()
    for package in client.channel.software.listAllPackages(key,DESTINATION['label'], FROM_DATE.isoformat(), TO_DATE.isoformat()) :
        packages_in_destination.append(package['id'])
    # import itertools 
    # final_package_list = list(itertools.filterfalse(lambda x: x in packages_in_destination, package_list)) + list(itertools.filterfalse(lambda x: x in package_list, packages_in_destination))
    final_package_list=[package for package in packages_in_destination if package not in package_list]
else:
    final_package_list = package_list
#avoid sync issues, remove any duplicated ids
final_package_list = list(set(final_package_list))
if len(final_package_list) > 0 :
    print "%d unique packages selected" % (len(final_package_list))
    passes = len(final_package_list) / 100
    last_pass = False
    if len(errata_list) % 100 > 0 :
        passes = passes + 1
        last_pass = True
    packages_to_push = list()
    packages_pushed = 0
    current_pass = 1
    for package in final_package_list:
        packages_to_push.append(package)
        print '\r'+"%d packages prepared out of %d (pass %d of %d)%s" % (len(packages_to_push),len(errata_list),current_pass,passes, "                   "),
        if len(packages_to_push) == 100:
            if DEBUG >= 3:
                print "" # new line not to overwrite the previous one
                print "%d packages to push in pass %d:" % (len(packages_to_push),current_pass)
                if DEBUG >= 6:
                    for package in packages_to_push:
                        print " - ID %d" % (package)
            result = client.channel.software.addPackages(key,DESTINATION['label'],packages_to_push)
            # addpackages returns 1 if the operation was a success, otherwise throws an error
            if result == 1:
                packages_pushed = packages_pushed + len(packages_to_push)
            print '\r'+"%d packages pushed out of %d (pass %d of %d)%s" % (packages_pushed,len(packages_list),current_pass,passes, "                     "),
            current_pass = current_pass + 1
            packages_to_push = list()
    if last_pass == True:
        result = client.channel.software.mergeErrata(key,SOURCE,DESTINATION['label'],erratas_to_push)
        if result == 1:
            packages_pushed = packages_pushed + len(packages_to_push)
        print '\r'+"%d erratas pushed out of %d (pass %d of %d)%s" % (erratas_pushed,len(errata_list),current_pass,passes, "                    "),
    print "" #avoid writing next line to the same line
else:
    print "no package selected"

#plan the regeneration of the repodata
client.channel.software.regenerateYumCache(key,DESTINATION['label'])
print "regeneration of repodata requested for %s" % (DESTINATION['label'])

print "script finished"
client.auth.logout(key)