#
# Module to simulate js
# challenge when loading leagues
# from Betvictor.com.
#
# Takes a scrapy response obj, strips
# the initial params (c,slt,s1,s2..)
# , simulates the javascript computation on them
# and returns the value of TS644333_75.
#
# See myNotes/Betvictor_writeup.txt for more.
#
#
from scrapy.selector import Selector
import re

def process_script(response):

        # Log initial GET response for debugging.
        # with open('Betvictor_initial.html','w') as bvif:
        #    print >> bvif, response.body

        sel = Selector(response)

        all_scripts=sel.xpath('//script')
        wanted_script = all_scripts[0]

        #
        # Splitlines and regex to get initial parameters.
        #

        #get table
        table_line = wanted_script.extract().splitlines()[2].split('=')[-1].strip()
        matches=re.findall(r'\"(.+?)\"',table_line)
        if matches:
            table = matches[0]
        #get c
        c_line = wanted_script.extract().splitlines()[3]
        c = int(c_line.split('=')[-1].strip())
        #get slt
        slt_line = wanted_script.extract().splitlines()[4]
        matches=re.findall(r'\"(.+?)\"',slt_line)
        if matches:
            slt = matches[0]
        #get s1
        s1_line = wanted_script.extract().splitlines()[5]
        matches=re.findall(r"\'(.+?)\'",s1_line)
        if matches:
            s1= matches[0]
        #get s2
        s2_line = wanted_script.extract().splitlines()[6]
        matches=re.findall(r"\'(.+?)\'",s2_line)
        if matches:
            s2= matches[0]
        #get n
        n_line = wanted_script.extract().splitlines()[7]
        n = int(n_line.split('=')[-1].strip())
        #document.forms[0].elements[1].value="cebe976fc0b64cd998dec7348d664193:"+...
        # value_line = wanted_script.extract().splitlines()[-5].split('=')[1]
        # value = None  # Initialize
        # matches=re.findall(r'\"(.+?)\"',value_line)
        # if matches:
        #     value= matches[0]
        value_line = wanted_script.extract().splitlines()[-1].split('=')[1]
        matches = re.findall(r'^\"(.+?)\"', value_line)
        if matches:
            value= matches[0]

        print '*'*100
        print '\033[1;4m Initial Parameters \033[0m'
        #print '\033[7m table: \033[0m %s' % table
        print 'c: \033[7m %s \033[0m, slt: \033[7m %s \033[0m, s1: \033[7m %s \033[0m, s2: \033[7m %s \033[0m, n: \033[7m %s \033[0m, value: \033[7m %s \033[0m' % (c,slt,s1,s2,n,value)
        print '*'*100

        # Now replicate js script action with these params
        start = ord(s1[0])
        end   = ord(s2[0])
        m = pow(((end - start) + 1),n)


        print '\033[7m Computed: start: %s, end: %s, m: %s \033[0m' % (start,end,m)


        arr = {}
        for i in range(n):
            arr[i] = s1

        for i in range(m-1):

            for j in range(n-1, -1,-1):

                t = ord(arr[j][0])+1
                arr[j] = chr(t)

                if ord(arr[j][0]) <= end:
                    break
                else:  arr[j] = s1

            chlg = "".join(arr.values())
            str = chlg + slt

            #with open('Betvictor_permuations.log','a') as f:
            #    print >>f, 'DEBUG: At i: %s, chlg: %s, str: %s, slt: %s ' % (i, chlg,str,slt)
            #    print >>f, 'DEBUG: At i: arr %s' % (arr)

            #print  '\033[7m DEBUG: At i: %s, chlg: %s, str: %s, slt: %s' % (i, chlg,str,slt)

            crc = 0
            #Bitwise XOR
            crc = crc ^ (-1)

            #print 'Initial table index: i:', i, ' is:', ((crc ^ ord(str[0])) & int('000000FF',16))*9

            iTop = len(str)
            for k in range(iTop):
               ind1 = ((crc ^ ord(str[k])) & int('000000FF',16))*9

               #with open('Betvictor_bitwise.log','a') as jf:
               #    print>>jf, 'iTop:', iTop
               #    print>>jf, 'i:',i
               #    print>>jf, 'k:',k
               #    print >>jf, 'crc:',crc #, ' type_crc:', type(crc)
               #    print >>jf, 'ind1:', ind1 #, ' type_ind1:', type(ind1)
               #    print >>jf,'table value:', table[ind1: ind1+8]

               # Because python has arbitrary precision ints
               # and js truncates to 32bit, we must simulate
               # 32 bit ints by masking.
               # see http://stackoverflow.com/questions/22518641/
               # why-does-this-bitwise-operation-not-give-same-result-
               # in-python-and-js?noredirect=1#comment34265098_22518641
               x = int(table[ind1: ind1+8],16)
               x = x & 0xFFFFFFFF   # Keep only 32 bits
               if x >= 0x80000000:
                   # Consider it a signed value (0x80000000 is 2147483648 2^32 over 2)
                   x = -(0x100000000 - x)    # (0x100000000 is 2^32)

               crc = (crc >> 8) ^ x


            crc =  crc ^ (-1)

            crc = abs(crc)

            if crc == int(c): break

        value = value + chlg + ":" + slt + ":" + unicode(crc)

        return value.strip()

