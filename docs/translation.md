OSR is an international community and there is a collective effort to translate the website.

There are two areas that needs work:
1. marking strings to be translated in our templates.
2. translate the strings.


## 1. Marking the strings
Our HTML is rendered from django templates located in the `/templates/` folders of our apps.

Here are quick links to our templates folders:

* [leagues](/league/templates)
* [communities](/community/templates/community)
* [tournament](/tournament/templates/tournament)
* [calendar](/fullcalendar/templates/fullcalendar)
* [main folder](/openstudyroom/templates)

You need to mark the strings you want to be translated as follow:
- using [trans template tag](https://docs.djangoproject.com/en/2.1/topics/i18n/translation/#trans-template-tag) like that: `{% trans "string" %}`. Those shouldn't contain any template variable.
- using [blocktrans template tag](https://docs.djangoproject.com/en/2.1/topics/i18n/translation/#blocktrans-template-tag) like that: `{% blocktrans with variable=a_thing %} a long string with a {{variable}} in it {% endblocktrans %}`

Be sure that `i18n` tags are loaded on this template with `{% load other_tags i18n %}` at the beginning of the file.

Please edit or PR such changes in our "localisation" branch. Don't worry we will proof read your edit and they won't be on production automatically.

Note: you can add [comments](https://docs.djangoproject.com/en/2.1/topics/i18n/translation/#comments-for-translators-in-templates) for the translators: `{% comment %}Translators: some comments helping translators{% endcomment %}`. Those comments will not appear in the html but will be available for translators.


## 2. Translate the strings:

Translation Poeditor is kindly hosting our translation [here](https://poeditor.com/projects/view?id=232175) to promote free software.

Please reach OSR team on discord if you want to help us translate into any language.