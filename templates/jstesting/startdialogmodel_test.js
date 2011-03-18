{% extends "jstesting/base_test.html" %}
{% block testscript %}

var MS_model = null;

function makeBaseJSON() {
    return {
        'my_languages': ['en', 'fr'],
        'original_language': 'en',
        'video_languages': [
            { 'language': 'en', 'dependent': false, 'is_complete': true },
            { 'language': 'fr', 'dependent': false, 'is_complete': false }
        ]
    };
}

function setUp() {
    mirosubs.languages = {{languages|safe}};
}

function testOriginalLanguageDisplay() {
    var model = new mirosubs.startdialog.Model(makeBaseJSON());
    assertFalse(model.originalLanguageShown());

    var json = makeBaseJSON();
    json['original_language'] = '';
    json['video_languages'] = [];
    var model = new mirosubs.startdialog.Model(json);
    assertTrue(model.originalLanguageShown());
}

function testToLanguages0() {
    var model = new mirosubs.startdialog.Model(makeBaseJSON());
    
    var languages = model.toLanguages();
    assertEquals('fr', languages[0].language);
    assertEquals('en', languages[1].language);
    assertEquals('fr', model.getSelectedLanguage().language);

    model.selectLanguage(languages[1]);
}

function testToLanguages1() {
    var model = new mirosubs.startdialog.Model(makeBaseJSON());
    var languages = model.toLanguages();
    assertTrue(languages.length > 2)
    assertEquals(1, goog.array.filter(
        languages, function(l) {
            return l.language == 'en'
        }).length);
    assertEquals(1, goog.array.filter(
        languages, function(l) {
            return l.language == 'fr'
        }).length);
}

function testToLanguages2() {
    var json = makeBaseJSON();
    json['original_language'] = '';
    json['video_languages'] = [];
    var model = new mirosubs.startdialog.Model(json);
    var languages = model.toLanguages();
    assertTrue(languages[0].language == 'en' || languages[0].language == 'fr');
    assertTrue(languages[0].language != languages[1].language && 
               (languages[1].language == 'en' || languages[1].language == 'fr'));
    assertTrue(languages.length > 2);
}

function testToLanguagesWithUnsubtitledLanguage() {
    var json = makeBaseJSON();
    json['my_languages'].push('de');
    var model = new mirosubs.startdialog.Model(json);
    var languages = model.toLanguages();
    assertEquals('de', languages[0].language);
    assertEquals('fr', languages[1].language);
    assertEquals('en', languages[2].language);
}

function testToLanguagesWithDependent0() {
    var json = makeBaseJSON();
    json['my_languages'] = ['it', 'fr'];
    json['video_languages'].push({
        'language': 'it', 'dependent': true, 'percent_done': 50, 'standard': 'fr'
    })
    var model = new mirosubs.startdialog.Model(json);
    var languages = model.toLanguages();
    assertEquals('it', languages[0].language);
    assertEquals('fr', languages[1].language);
}

function testFromLanguages0() {
    var model = new mirosubs.startdialog.Model(makeBaseJSON());
    var fromLanguages = model.fromLanguages();
    assertEquals(1, fromLanguages.length);
    assertEquals('en', fromLanguages[0].LANGUAGE);
    model.selectLanguage(model.toLanguages()[1]);
    fromLanguages = model.fromLanguages();
    assertEquals(1, fromLanguages.length);
    assertEquals('fr', fromLanguages[0].LANGUAGE);
}



{% endblock %}