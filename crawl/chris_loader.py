import json
import codecs
import re


# Validation of URLS
def isValidURL(stringed):
    # Regex to check valid URL
    regex = ("((http|https)://)(www.)?" +
             "[a-zA-Z0-9@:%._\\+~#?&//=]" +
             "{2,256}\\.[a-z]" +
             "{2,6}\\b([-a-zA-Z0-9@:%" +
             "._\\+~#?&//=]*)")

    # Compile the ReGex
    complied_regex = re.compile(regex)

    # If the string is empty
    # return false
    if stringed is None:
        return False

    # Return if the string
    # matched the ReGex
    if re.search(complied_regex, stringed):
        return True
    else:
        return False

# READ all (30) given charity URLS and append them in a list
def get_websites_for_open_wpm(f):
    data = json.load(codecs.open(f, 'r', 'utf-8-sig'))
    charity_websites = []
    index = 1
    for d in data:
        charity_website = d['charity_contact_web']
        # Check if given URL is valid
        if isValidURL(charity_website):
            charity_websites.append(charity_website)
            index += 1
    return charity_websites


def load_websites(f):
    yes_websites = []
    other_larger_domains = []
    for web_url in get_websites_for_open_wpm(f):
        web_url.lower()
        if web_url.endswith(".edu") or web_url.endswith(".ac.uk"):
            other_larger_domains.append(web_url)
        elif web_url.find("wordpress.com") != -1:
            other_larger_domains.append(web_url)
        elif web_url.find("wix.com") != -1:
            other_larger_domains.append(web_url)
        elif web_url.find("web.com") != -1:
            other_larger_domains.append(web_url)
        elif web_url.find("constantcontact.com") != -1:
            other_larger_domains.append(web_url)
        elif web_url.find("hostgator.com") != -1:
            other_larger_domains.append(web_url)
        elif web_url.find("wpbeaverbuilder.com") != -1:
            other_larger_domains.append(web_url)
        elif web_url.find("weebly.com") != -1:
            other_larger_domains.append(web_url)
        elif web_url.find("squarespace.com") != -1:
            other_larger_domains.append(web_url)
        elif web_url.find("webnode.co.uk") != -1:
            other_larger_domains.append(web_url)
        elif web_url.find("jimdo.com") != -1:
            other_larger_domains.append(web_url)
        elif web_url.find("duda.co") != -1:
            other_larger_domains.append(web_url)
        elif web_url.find("webflow.com") != -1:
            other_larger_domains.append(web_url)
        elif web_url.find("one.com") != -1:
            other_larger_domains.append(web_url)
        elif web_url.find("mozello.com") != -1:
            other_larger_domains.append(web_url)
        elif web_url.find("webstarts.com") != -1:
            other_larger_domains.append(web_url)
        elif web_url.find("mobirise.com") != -1:
            other_larger_domains.append(web_url)
        else:
            yes_websites.append(web_url)
    return yes_websites

