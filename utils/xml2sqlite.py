#!/bin/env python3
from xml.dom import minidom
import sqlite3
import unicodedata
conn = sqlite3.connect('../assets/conjugation.db')

def get_text(node):
    if node.firstChild == None:
        return None
    return node.firstChild.nodeValue

def get_first(node, childClass):
    return node.getElementsByTagName(childClass)[0]


def remove_accents(input_str):
    if input_str is None:
        return None
    nkfd_form = unicodedata.normalize('NFKD', input_str)
    return u"".join([c for c in nkfd_form if not unicodedata.combining(c)])

def hash_32_bit(input_str):
    import hashlib
    return int(
        hashlib.sha256(input_str.encode('utf-8')).hexdigest()[-8:],
        16
    )


xmldoc = minidom.parse('../data/verbs-fr.xml')
verbs = xmldoc.getElementsByTagName('v');


verbTypes = {}
verbTypesCounter = 1

# we build the list of verbs
conn.execute(
    '''
    CREATE TABLE verb (
        _id INTEGER PRIMARY KEY,
        verb_type_id INTEGER,
        infinitive TEXT,
        infinitive_ascii TEXT,
        infinitive_ascii_hash TEXT,
        radical TEXT,
        radical_ascii TEXT,
        h_aspired BOOL
    )
    '''
)
for oneVerb in verbs:
    infinitive = get_text(get_first(oneVerb, 'i'))
    verbType = get_text(get_first(oneVerb, 't'))
    isInitialHPronounced = len(oneVerb.getElementsByTagName('aspirate-h')) == 1


    if verbType not in verbTypes:
        verbTypes[verbType] = verbTypesCounter
        verbTypesCounter += 1

    verbTypeId = verbTypes[verbType]
    radical = infinitive[:-len(verbType.split(':')[1])]

    conn.execute(
        '''
        INSERT INTO verb
        VALUES(
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?
        )
        ''',
        [

            hash_32_bit(infinitive),
            verbTypeId,
            infinitive,
            remove_accents(infinitive),
            hash_32_bit(remove_accents(infinitive)),
            #to get the radical we remove the suffix part that we
            #got from the verb type
            radical,
            remove_accents(radical),
            isInitialHPronounced
        ]
    )
conn.execute(
    '''
    CREATE INDEX idx_verb_infinitive_ascii_hash
    ON verb (infinitive_ascii_hash ASC)
    '''
);
conn.commit()

# we build the list of verb types
conn.execute(
    '''
    CREATE TABLE verb_type (
        id INTEGER PRIMARY KEY,
        base TEXT,
        part_to_replace TEXT
    )
    '''
)

for verbType, verbTypeId in verbTypes.items():
    conn.execute(
        'INSERT INTO verb_type VALUES(?, ?, ?)',
        [verbTypeId, verbType.replace(':', ''), verbType.split(':')[1]]
    )
conn.commit()


xmldoc = minidom.parse('../data/conjugation-fr.xml')


# we build the list of type of conjugation
MODES = {
    'infinitive' : 0,
    'indicative' : 1,
    'conditional' : 2,
    'subjunctive' : 3,
    'imperative' : 4,
    'participle' : 5
}

TENSES = {
    'infinitive-present' : 0,
    'present' : 1,
    'imperfect' : 2,
    'future' : 3,
    'simple-past' : 4,
    'imperative-present' : 5,
    'present-participle' : 6,
    'past-participle' : 7
}

NOBODY = 0 #for infinitive and participle
FIRST_SINGULAR = 1
SECOND_SINGULAR = 2
THIRD_SINGULAR = 3
FIRST_PLURAL = 4
SECOND_PLURAL = 5
THIRD_PLURAL = 6

SECOND_SINGULAR_IMPERATIVE = 7
FIRST_PLURAL_IMPERATIVE = 8
SECOND_PLURAL_IMPERATIVE = 9

# TODO for participle find something better
MASCULIN_SINGULAR = 10
FEMININ_SINGULAR = 11
MASCULIN_PLURAL = 12
FEMININ_PLURAL = 13


PERSONS_NORMAL_TENSE = frozenset([
    FIRST_SINGULAR,
    SECOND_SINGULAR,
    THIRD_SINGULAR,
    FIRST_PLURAL,
    SECOND_PLURAL,
    THIRD_PLURAL
])

PERSONS_IMPERATIVE_TENSE = frozenset([
    SECOND_SINGULAR_IMPERATIVE,
    FIRST_PLURAL_IMPERATIVE,
    SECOND_PLURAL_IMPERATIVE
])

FORMS_PAST_PARTICIPLE = frozenset([
    MASCULIN_SINGULAR,
    FEMININ_SINGULAR,
    MASCULIN_PLURAL,
    FEMININ_PLURAL
]);

conn.execute(
    '''
    CREATE TABLE conjugation (
        id INTEGER PRIMARY KEY,
        verb_type_id INTEGER NOT NULL,
        mode INTEGER NOT NULL,
        tense INTEGER NOT NULL,
        person INTEGER NOT NULL,
        suffix TEXT DEFAULT NULL,
        suffix_ascii TEXT DEFAULT NULL
    )
    '''
)

def parse_tense(
    verbe_type_id,
    mode,
    tense_name,
    persons_id_for_that_tense=PERSONS_NORMAL_TENSE
):

    tense = get_first(mode, tense_name)

    persons = tense.getElementsByTagName('p')

    for person_id, person in zip(persons_id_for_that_tense, persons):
        for inflection_node in person.getElementsByTagName('i'):
            inflection = get_text(inflection_node)
            conn.execute(
                '''
                INSERT INTO conjugation VALUES (
                    NULL,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?
                )
                ''',
                [
                    verbe_type_id,
                    MODES[mode.tagName],
                    TENSES[tense_name],
                    person_id,
                    inflection,
                    remove_accents(inflection)
                ]
            )



templates = xmldoc.getElementsByTagName('template')
for oneTemplate in templates:
    verbType = (oneTemplate.attributes['name'].value)
    verbTypeId = verbTypes[verbType]
    radical = verbType.split(':')[0]

    # Infinitive
    mode = get_first(oneTemplate, 'infinitive')

    parse_tense(
        verbTypeId,
        mode,
        'infinitive-present',
        persons_id_for_that_tense=[NOBODY]
    )

    # Indicative
    mode = get_first(oneTemplate, 'indicative')

    parse_tense(verbTypeId, mode, 'present')
    parse_tense(verbTypeId, mode, 'imperfect')
    parse_tense(verbTypeId, mode, 'future')
    parse_tense(verbTypeId, mode, 'simple-past')

    #Conditional
    mode = get_first(oneTemplate, 'conditional')

    parse_tense(verbTypeId, mode, 'present')
    #Subjunctive
    mode = get_first(oneTemplate, 'subjunctive')

    parse_tense(verbTypeId, mode, 'present')
    parse_tense(verbTypeId, mode, 'imperfect')

    #imperative
    mode = get_first(oneTemplate, 'imperative')

    parse_tense(
        verbTypeId,
        mode,
        'imperative-present',
        persons_id_for_that_tense=PERSONS_IMPERATIVE_TENSE
    )

    #participle
    mode = get_first(oneTemplate, 'participle')

    parse_tense(
        verbTypeId,
        mode,
        'present-participle',
        persons_id_for_that_tense=[NOBODY]
    )

    parse_tense(
        verbTypeId,
        mode,
        'past-participle',
        #Note: actually it's supposed to a special case as we store
        # masculine singular
        # feminine singular
        # masculine plural
        # feminine plural
        persons_id_for_that_tense=FORMS_PAST_PARTICIPLE
    )

conn.commit()


# create reverse look up tables
conn.execute(
    '''
    CREATE TABLE conjugated_form (
        id INTEGER PRIMARY KEY,
        conjugation_id INTEGER NOT NULL,
        verb_id INTEGER NOT NULL,
        conjugated TEXT,
        conjugated_ascii TEXT
    )
    '''
)

conn.execute(
    '''
    INSERT INTO conjugated_form
    SELECT
        NULL,
        c.id,
        v._id,
        radical || suffix,
        radical_ascii || suffix_ascii
    FROM verb v
    JOIN verb_type t ON t.id = v.verb_type_id
    JOIN conjugation c ON t.id = c.verb_type_id
    '''
)
conn.execute(
    '''
    CREATE INDEX idx_conjugated_form_conjugated
    ON conjugated_form (conjugated ASC)
    '''
);

conn.execute(
    '''
    CREATE INDEX idx_conjugated_form_conjugated_ascii
    ON conjugated_form (conjugated_ascii ASC)
    '''
);



# Insert mode
conn.execute(
    '''
    CREATE TABLE mode (
        id INT PRIMARY KEY,
        text
    )
    '''
)

conn.execute(
    '''
    INSERT INTO mode
    VALUES
        (0,  'infinitive'),
        (1,  'indicative'),
        (2, 'conditional'),
        (3, 'subjunctive'),
        (4,  'imperative'),
        (5,  'participle')
    '''
)
conn.commit()

# Insert tense
conn.execute(
    '''
    CREATE TABLE tense (
        id INT PRIMARY KEY,
        text
    )
    '''
)

conn.execute(
    '''
    INSERT INTO tense
    VALUES
        (0,     'present'),
        (1,     'present'),
        (2,   'imperfect'),
        (3,      'future'),
        (4, 'simple past'),
        (5,     'present'),
        (6,     'present'),
        (7,        'past')
    '''
)
conn.commit()

# Insert person
conn.execute(
    '''
    CREATE TABLE person (
        id INT PRIMARY KEY,
        base text,
        with_h_aspired text,
        explanation text
    )
    '''
)
conn.execute(
    '''
    INSERT INTO person
    VALUES
        (0,    "",      "", ""),
        (1,   "je",   "j'", "1st_singular"),
        (2,   "tu",   "tu", "2nd_singular"),
        (3,   "il",   "il", "3rd_singular"),
        (4, "nous", "nous", "1st_plural"),
        (5, "vous", "vous", "2nd_plural"),
        (6,  "ils",  "ils", "3rd_plural"),
        -- imperative
        (7,  "",  "", "2nd_singular"),
        (8,  "",  "", "1st_plural"),
        (9,  "",  "", "2nd_plural"),
        -- past participle
        (10, "", "", "masculin_singular"),
        (11, "", "", "feminin_singular"),
        (12, "", "", "masculin_plural"),
        (13, "", "", "feminin_plural")
    '''
)
conn.commit()

# Android metadata
conn.execute('CREATE TABLE android_metadata (locale TEXT);')
conn.execute('INSERT INTO android_metadata VALUES ("en_US");')
conn.commit()
