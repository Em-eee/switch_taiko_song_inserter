# Takes a WiiU XML decrypted music info bin and turns it into a JSON format for the Switch
# Read the Switch JSON first to create a merge: check numerical ids and song names for conflicts
# No point having the same song twice either

# Switch musicinfo is in musicinfo.bin as a gz packed JSON
# WiiU musicinfo is in in dp_pack.drp as musicinfo_db.bin as XML

#Script expects musicinfo (extracted from musicinfo.bin) and musicinfo_db.bin in the same folder, subject to change

#JSON format:

# uniqueId
# primary interger key probably. If this is too high (>= 200), the song will not load: Stuck on loading screen with no song name. OR load the last song played if you have one
# id
# string name of the song. No limit? longest name is "id":"furikatsu",
# songFileName
# Seems to pull from the SOUND folder no matter what? But only for the preview?
# Location of song file name. skips nus3bank extension. need to test case sensitivity
# order
# Order the song shows up in. Can be the same? Independnat of genre, which can make things really confusing
# genreNo
# 0 - Pop, 1 - Anime, 2 - Vocaloid, 3 - Variety, 4 - ???, 5 - Classical, 6 - Game, 7 - Namco Original
# secretFlag
# Has to be unlocked maybe?
# dlc
# Has to be purchased maybe?
# debug
# Debug songs?
# recording
# Allow recording probably? 
# branchEasy, branchNormal, branchHard, branchMania, branchUra
# If the song branches probably?
# starEasy, starNormal, starHard, starMania, starUra
# Number of stars for a song. Ura is 0 if it isn't there?
# shinutiEasy, shinutiNormal, shinutiHard, shinutiMania, shinutiUra
# shinutiEasyDuet, shinutiNormalDuet, shinutiHardDuet, shinutiManiaDuet, shinutiUraDuet
# points per beat in shinuti mode? Not sure
# scoreEasy, scoreNormal, scoreHard, scoreMania, scoreUra
# Max score? Not sure if needed or what it is for, need to test
# alleviationEasy, alleviationNormal, alleviationHard, alleviationMania, alleviationUra
# always false, have not seen one that is true. What is alleviation? 
# SONG_SOURYU seems to be the only song that uses it
# bgDon0, bgDancer0, chibi0, rendaEffect0, dancer0, feverEffect0, bgDon1, bgDancer1, bgFever1, chibi1, rendaEffect1, dancer1, feverEffect1
# All seem to be unused

import json
import xmltodict
import struct
import sys
import os
import gzip
import zlib
import shutil

switch_musicInfo = {}
wiiu_musicInfo = {}
wordlist = []

word_insert = {}
genre_order = [0, 0, 0, 0, 0, 0, 0, 0]

uid = 1

#Check if an ID is in the wiiu XML already
def checkID_wiiu(id):
    id = id.lower()
    #for (wiiu_musicInfo['DB_DATA']['DATA_SET'] as song):
    for song in wiiu_musicInfo['DB_DATA']['DATA_SET']:
        if (song['id'].lower() == id):
            return True
    return False

#Check if an ID is in the switch JSON already
def checkID_switch(id):
    id = id.lower()
    #for (wiiu_musicInfo['DB_DATA']['DATA_SET'] as song):
    for song in switch_musicInfo['items']:
        if (song['id'].lower() == id):
            return True
    return False


#Get an unused unique ID to use 
#TODO cannot be >= 200
def genUID():
    global uid
    
    modified = False
    for song in switch_musicInfo['items']:
        if song['uniqueId'] == uid:
            uid = uid + 1
            modified = True

    while modified:
        modified = False
        for song in switch_musicInfo['items']:
            if song['uniqueId'] == uid:
                uid = uid + 1
                modified = True

    return uid

def wiiuGenreSwap(number):
    if (number == 2):
        return 3
    if (number == 3):
        return 2
    return number

def getOrder(genreNo):
    global genre_order
    genre_order[genreNo] = genre_order[genreNo] + 1
    return genre_order[genreNo]

#Copied from https://gist.github.com/dantarion/c84e7ae618c18cb735342156e6bc8849 
#Also check https://github.com/anqurvanillapy/s0ngbrew/blob/master/s0ngbrew/codec.py
#filename is the file name we're looking for in the drp, as the drp can contain multiple files.
def drpExtract(drpFilename, filename = ''):
    f = open(drpFilename,"rb")
    f.seek(0x14)
    unknown, filecount = struct.unpack(">HH",f.read(4))
    f.seek(0x60)
    for i in range(0, filecount):
        fname = f.read(0x40).split(b'\x00')[0]
        #if os.path.isfile(os.path.join(dirpath,fname+".bin")):
        #    continue
        
        #print "\t",fname,
        f.seek(0x10,1)
        fsize, fsize2, fsize3, fsize4,uncompressedSize = struct.unpack(">5I",f.read(4*5))
        #print fsize, fsize2, fsize3, fsize4,hex(uncompressedSize)
        data = f.read(fsize2-4)
        if fsize > 80:
            data = zlib.decompress(data)

        #If this is proper name, we've got the file!
        # Second check, if this is the only file, we don't need to check the name
        if fname.decode('ascii') == filename or filecount == 1:
            return data
        #ut = open(os.path.join(dirpath,fname+".bin"),"wb")
        #out.write(data)
        #out.close()
    print ("DRP Extract error ", drpFilename, filename)
    sys.exit()

#weak ass ASCII check
def is_ascii(s):
    return all(ord(c) < 128 for c in s)

#convert the file from big endianess to little endianess
#Copied from https://pastebin.com/yx8v9MkG
def copyandconvert(inFile, outFile):
    obo = '<'
    ibo = '>'
    with open(inFile, 'rb') as fin:
        with open(outFile, 'wb') as fout:
            for hanteiI in range(36 * 3):
                fout.write(struct.pack(obo + 'f', struct.unpack(ibo + 'f', fin.read(4))[0])) # hantei notes
            
            while fin.tell() != 0x200:
                fout.write(struct.pack(obo + 'I', struct.unpack(ibo + 'I', fin.read(4))[0])) # header stuff like tamashii rate
            
            num_section = struct.unpack(ibo + 'I', fin.read(4))[0]
            fout.write(struct.pack(obo + 'I', num_section)) # num_section
            fout.write(struct.pack(obo + 'I', struct.unpack(ibo + 'I', fin.read(4))[0])) # unknown
            
            for sectionI in range(num_section):
                #print(fin.tell())
                fout.write(struct.pack(obo + 'f', struct.unpack(ibo + 'f', fin.read(4))[0])) # bpm
                fout.write(struct.pack(obo + 'f', struct.unpack(ibo + 'f', fin.read(4))[0])) # start_time
                fout.write(struct.pack(obo + 'B', struct.unpack(ibo + 'B', fin.read(1))[0])) # gogo
                fout.write(struct.pack(obo + 'B', struct.unpack(ibo + 'B', fin.read(1))[0])) # section_line
                fout.write(struct.pack(obo + 'H', struct.unpack(ibo + 'H', fin.read(2))[0])) # unknown
                
                for bunkiI in range(6):
                    fout.write(struct.pack(obo + 'I', struct.unpack(ibo + 'I', fin.read(4))[0])) # bunkis
                
                fout.write(struct.pack(obo + 'I', struct.unpack(ibo + 'I', fin.read(4))[0])) # unknown
                
                for routeI in range(3):
                    num_notes = struct.unpack(ibo + 'H', fin.read(2))[0]
                    fout.write(struct.pack(obo + 'H', num_notes)) # num_notes
                    fout.write(struct.pack(obo + 'H', struct.unpack(ibo + 'H', fin.read(2))[0])) # unknown
                    fout.write(struct.pack(obo + 'f', struct.unpack(ibo + 'f', fin.read(4))[0])) # scroll
                    
                    for noteI in range(num_notes):
                        note_type = struct.unpack(ibo + 'I', fin.read(4))[0]
                        fout.write(struct.pack(obo + 'I', note_type)) # note_type
                        fout.write(struct.pack(obo + 'f', struct.unpack(ibo + 'f', fin.read(4))[0])) # headerI1

                        #fout.write(struct.pack(obo + 'I', struct.unpack(ibo + 'I', fin.read(4))[0])) # item
                        #Not sure if all of them are 16int, but the first one is for sure
                        fout.write(struct.pack(obo + 'B', struct.unpack(ibo + 'B', fin.read(1))[0])) # item
                        fout.write(struct.pack(obo + 'B', struct.unpack(ibo + 'B', fin.read(1))[0])) # item???
                        fout.write(struct.pack(obo + 'B', struct.unpack(ibo + 'B', fin.read(1))[0])) # item??
                        fout.write(struct.pack(obo + 'B', struct.unpack(ibo + 'B', fin.read(1))[0])) # item??

                        fout.write(struct.pack(obo + 'f', struct.unpack(ibo + 'f', fin.read(4))[0])) # unknown1
                        fout.write(struct.pack(obo + 'H', struct.unpack(ibo + 'H', fin.read(2))[0])) # hit
                        fout.write(struct.pack(obo + 'H', struct.unpack(ibo + 'H', fin.read(2))[0])) # score_inc
                        fout.write(struct.pack(obo + 'f', struct.unpack(ibo + 'f', fin.read(4))[0])) # length
                        
                        if note_type in [6, 9, 98]:
                            fout.write(struct.pack(obo + 'I', struct.unpack(ibo + 'I', fin.read(4))[0])) # unknown
                            fout.write(struct.pack(obo + 'I', struct.unpack(ibo + 'I', fin.read(4))[0])) # unknown


with gzip.open('switch/Data/NX/datatable/musicinfo.bin', 'rb') as musicinfo:
    switch_musicInfo = json.load(musicinfo)
    print(switch_musicInfo['items'])

with open('word_insert', encoding="utf8") as word_insert_file:
    word_insert = json.load(word_insert_file)

#with open('musicinfo_db.bin', "rb") as musicinfo:
#    wiiu_musicInfo = xmltodict.parse(musicinfo)
#    #print(wiiu_musicInfo)

wiiu_musicInfo = xmltodict.parse(drpExtract('wiiu3/content/Common/database/db_pack.drp', 'musicinfo_db'))
print(wiiu_musicInfo)

#set all the songs to be playable and recordable, might as well
for song in switch_musicInfo['items']:
    song['dlc'] = False
    song['secretFlag'] = False
    song['recording'] = True

    if genre_order[song['genreNo']] < song['order']:
        genre_order[song['genreNo']] = song['order']

if not os.path.exists('romfs/Data/NX/sound'):
    os.makedirs('romfs/Data/NX/sound')

#song time
for song in wiiu_musicInfo['DB_DATA']['DATA_SET']:
    if checkID_switch(song['id']):
        print("Duplicate song: " + song['id'])
        continue
    if song['debug'] is not None: 
        print("Debug: " + song['id'])
        continue #No point doing debug songs really
    elif song['ura'] == '\u25cb':
        print("Ura song: " + song['id'][3:])

        found = False
        for modSong in switch_musicInfo['items']:
            if (modSong['id'] == song['id'][3:]): #cut off first 3 letters. ura songs all start with ex_?
                found = True

                #Ura song already set: duplicate ura!
                if modSong['starUra'] > 0:
                    break

                #Ura songs seem to just use the mania stars
                modSong['starUra'] = int(song['starMania'])
                #branch mania seems to do the same, see ex_butou2
                modSong['branchUra'] = song['branchMania'] == '\u25cb'

                path = 'romfs/Data/NX/fumen/enso/' +  song['id'][3:]
                if not os.path.exists(path):
                    os.makedirs(path)

                #Ura songs just take the ex_ID_m version in the WiiU version, but have a proper id_x.bin in the Switch version
                copyandconvert('wiiu3/content/wiiu/fumen/solo/' + song['id'][3:]+ '_m.bin', path + '/' + song['id'][3:] + '_x.bin')
                copyandconvert('wiiu3/content/wiiu/fumen/duet/' + song['id'][3:] + '_m_1.bin', path + '/' + song['id'][3:] + '_x_1.bin')
                copyandconvert('wiiu3/content/wiiu/fumen/duet/' + song['id'][3:] + '_m_2.bin', path + '/' + song['id'][3:] + '_x_2.bin')
                break

        if found == False:
            print("Error no not-ura version" + song['id'][3:])
    else:
        #TODO not copy songs if they already exist
        shutil.copy('wiiu3/content/wiiu/sound/SONG_' + song['id'].upper() + ".nus3bank", 'romfs/Data/NX/sound/')

        path = 'romfs/Data/NX/fumen/enso/' + song['id']
        if not os.path.exists(path):
            os.makedirs(path)
        copyandconvert('wiiu3/content/wiiu/fumen/solo/' + song['id'] + '_e.bin', path + '/' + song['id'] + '_e.bin')
        copyandconvert('wiiu3/content/wiiu/fumen/solo/' + song['id'] + '_n.bin', path + '/' + song['id'] + '_n.bin')
        copyandconvert('wiiu3/content/wiiu/fumen/solo/' + song['id'] + '_h.bin', path + '/' + song['id'] + '_h.bin')
        copyandconvert('wiiu3/content/wiiu/fumen/solo/' + song['id'] + '_m.bin', path + '/' + song['id'] + '_m.bin')
        #x is ura!
        copyandconvert('wiiu3/content/wiiu/fumen/duet/' + song['id'] + '_e_1.bin', path + '/' + song['id'] + '_e_1.bin')
        copyandconvert('wiiu3/content/wiiu/fumen/duet/' + song['id'] + '_e_2.bin', path + '/' + song['id'] + '_e_2.bin')
        copyandconvert('wiiu3/content/wiiu/fumen/duet/' + song['id'] + '_n_1.bin', path + '/' + song['id'] + '_n_1.bin')
        copyandconvert('wiiu3/content/wiiu/fumen/duet/' + song['id'] + '_n_2.bin', path + '/' + song['id'] + '_n_2.bin')
        copyandconvert('wiiu3/content/wiiu/fumen/duet/' + song['id'] + '_h_1.bin', path + '/' + song['id'] + '_h_1.bin')
        copyandconvert('wiiu3/content/wiiu/fumen/duet/' + song['id'] + '_h_2.bin', path + '/' + song['id'] + '_h_2.bin')
        copyandconvert('wiiu3/content/wiiu/fumen/duet/' + song['id'] + '_m_1.bin', path + '/' + song['id'] + '_m_1.bin')
        copyandconvert('wiiu3/content/wiiu/fumen/duet/' + song['id'] + '_m_2.bin', path + '/' + song['id'] + '_m_2.bin')

        # new song
        newSong = {
			"uniqueId":genUID(),
			"id": song['id'],
			"songFileName": "sound/" + song['songFileName'], #turns it into wiiu3/song/whatever Might need better names here
			"order":getOrder(wiiuGenreSwap(int(song['genreNo']))),
            #wiiu 3 is Vocaloid rather than Variety, 2 is Variety so swap 2/3
			"genreNo":wiiuGenreSwap(int(song['genreNo'])),
			"secretFlag":False,
			"dlc":False,
			"debug":False,
			"recording":True,
             #when it's true it contains ○, false it'll be null
			"branchEasy": song['branchEasy'] == '\u25cb',
			"branchNormal": song['branchNormal'] == '\u25cb',
			"branchHard": song['branchHard'] == '\u25cb',
			"branchMania": song['branchMania'] == '\u25cb',
			#"branchUra": song['branchUra'] == '\u25cb',
            "branchUra": False, # I guess no Ura branches
			"starEasy": int(song['starEasy']),
			"starNormal": int(song['starNormal']),
			"starHard": int(song['starHard']),
			"starMania": int(song['starMania']),
            #Ura songs are no longer seperate in the Switch version, but are on the WiiU
			"starUra": 0,
			"shinutiEasy":3720,
			"shinutiNormal":2510,
			"shinutiHard":1570,
			"shinutiMania":1120,
			"shinutiUra":1000,
			"shinutiEasyDuet":3720,
			"shinutiNormalDuet":2510,
			"shinutiHardDuet":1570,
			"shinutiManiaDuet":1120,
			"shinutiUraDuet":1000,
            #still don't know what these are for, here's some random numbers
			"scoreEasy":400000,
			"scoreNormal":800000,
			"scoreHard":900000,
			"scoreMania":1100000,
			"scoreUra":1200000,
			"alleviationEasy": False,
			"alleviationNormal":False,
			"alleviationHard":False,
			"alleviationMania":False,
			"alleviationUra":False,
            "bgDon0":"",
			"bgDancer0":"",
			"bgFever0":"",
			"chibi0":"",
			"rendaEffect0":"",
			"dancer0":"",
			"feverEffect0":"",
			"bgDon1":"",
			"bgDancer1":"",
			"bgFever1":"",
			"chibi1":"",
			"rendaEffect1":"",
			"dancer1":"",
			"feverEffect1":""
        }

        switch_musicInfo['items'].append(newSong)

        # Word lists keys: 
        # song_sub_ID for the text under. usually FROM, or the singer
        # song_detail_ID for above. Original japanese name
        # song_eva actual name. big

        #font Type 3 is english, 0 is japanese? 2 for korean? 1 for chinese?


        if song['id'] in word_insert:
            wordlist.append(
                {
                    "key":"song_" + song['id'],
                    "japaneseText": song['title'],
                    "englishUsText": word_insert[song['id']]['name'],
                    "englishUsFontType": 3
                }
            )
            wordlist.append(  
                {
                    "key":"song_detail_" + song['id'],
                    "japaneseText": '',
                    "englishUsText": word_insert[song['id']]['original_name'],
                    "englishUsFontType": 0
                } 
            )
            wordlist.append(
                {
                    "key":"song_sub_" + song['id'],
                    "japaneseText": "",
                    "englishUsText": word_insert[song['id']]['bottom_text'],
                    "englishUsFontType": 3
                } 
            )
        else:
            wordlist.append(
                {
                    "key":"song_" + song['id'],
                    "japaneseText": song['title'],
                    "englishUsText": song['title'] if is_ascii(song['title']) else 'TODO',
                    "englishUsFontType": 3
                }
            )
            wordlist.append(  
                {
                    "key":"song_detail_" + song['id'],
                    "japaneseText": '',
                    "englishUsText": song['title'] if is_ascii(song['title']) == False else "",
                    "englishUsFontType": 0
                } 
            )
            wordlist.append(
                {
                    "key":"song_sub_" + song['id'],
                    "japaneseText": "",
                    "englishUsText": "",
                    "englishUsFontType": 3
                } 
            )
        
#output list of songs that are in both musicinfos. Those will be used to skip later I guess

if not os.path.exists('romfs/Data/NX/datatable'):
    os.makedirs('romfs/Data/NX/datatable')

#Defaults to max compression. Don't think I care.
file = gzip.open('romfs/Data/NX/datatable/musicinfo', 'w')
file.write(json.dumps(switch_musicInfo, indent='\t', separators=(',',':')).encode('UTF-8'))
file.close()

#Not sure if the gzipped file has to have the specific name
os.rename('romfs/Data/NX/datatable/musicinfo', 'romfs/Data/NX/datatable/musicinfo.bin')

#the word list for the names
with gzip.open('switch/Data/NX/datatable/wordlist.bin', 'rb') as musicinfo:
    wordy_list = json.load(musicinfo)
    wordy_list['items'].extend(wordlist)
    file = gzip.open('romfs/Data/NX/datatable/wordlist', 'w')
    file.write(json.dumps(wordy_list, indent='\t', separators=(',',':'), ensure_ascii=False).encode('UTF-8'))
    file.close()
    os.rename('romfs/Data/NX/datatable/wordlist', 'romfs/Data/NX/datatable/wordlist.bin')

#enso_chara Character unlocking, because why not
with gzip.open('switch/Data/NX/datatable/enso_chara.bin', 'rb') as enso_chara:
    characters = json.load(enso_chara)
    for char in characters['items']:
        char['secretFlag'] = False
        char['dlcFlag'] = False

    file = gzip.open('romfs/Data/NX/datatable/enso_chara', 'w')
    file.write(json.dumps(characters, indent='\t', separators=(',',':'), ensure_ascii=False).encode('UTF-8'))
    file.close()
    os.rename('romfs/Data/NX/datatable/enso_chara', 'romfs/Data/NX/datatable/enso_chara.bin')


#TODO I have no clue what the difference is with these, but some characters use them
# So let's just copy them all
shutil.copytree('romfs/Data/NX/fumen', 'romfs/Data/NX/fumen_hitnarrow')
shutil.copytree('romfs/Data/NX/fumen', 'romfs/Data/NX/fumen_hitwide')
