from __future__ import division  # nice division
import difflib  # for string comparison
import unicodedata  # Normalize unicode by forcing to ascii equiv in compStr

# if str is in dictionary of aliases replace by standard:
# should be pickled eventually or some such.
ALIASES = {'manchester city': ['man city', 'man.city'],
           'manchester united': ['man united', 'man u', 'man utd',
                                 'manchester u', 'manchester utd'],
           'cordoba': ['cordoba cf', ],
           'evian thonon gaillard': ['evian tg', ],
           'paris saint germain': ['paris sg', 'paris st-g', 'paris st g',
                                   'paris st germain', 'paris st.g',
                                   'paris st.germain', ],
           'qpr': ["queen's park rangers", ],
           'atletico madrid': ['atl madrid', ],
           'rayo vallecano': ['vallecano', ],
           'blackburn rovers': ['blackburn', ],
           'bayern munich': ['b munich', ],

           }


def compStr(str1, str2):
    '''
    Decide if two teams from different books are really the same.
    '''
    str1, str2 = str1.lower(), str2.lower()

    # Force unicode chars to ascii equiv, e.g. accented 'a' to regular 'a'
    try:
        str1 = unicodedata.normalize('NFKD', str1).encode('ascii', 'ignore')
        str2 = unicodedata.normalize('NFKD', str2).encode('ascii', 'ignore')
    except TypeError:
        # if strings are plain text not unicode
        pass
    aliases = ALIASES
    for key in aliases:
        if str1 in aliases[key]:
            str1 = key
        if str2 in aliases[key]:
            str2 = key

    # Is either simply contained in other? (e.g. man city and man city fc)
    if (str1 in str2) or (str2 in str1):
        return True

    # Resort to similiary testing. Quite unlikely both home/away will fail this.
    critVal = 0.8
    try:
        # The first arg allows junk ignore if set
        similarity = difflib.SequenceMatcher(None, str1, str2).ratio()
        if similarity > critVal:
                # Write str2 to str1 key of list in mongo overtime building up
                # lists we can maybe use to auto build alias dic
                return True
        else:
            return False
    except UnicodeEncodeError as e:
        print 'Unicode Error: %s.' % e
        print str1.encode('utf-8'), str2.encode('utf-8')
        return False
