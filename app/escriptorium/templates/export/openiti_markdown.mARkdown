{% load export_tags %}######OpenITI#

{% if part.source %}
#META# SOURCE: {{ part.source }}
{% endif %}
#META# CREATED: {% current_time %}

#META# CREATED BY: eScriptorium v{{ version }}

#META# IMAGE FILENAME: {{ part.filename }}

#META# IMAGE WIDTH: {{ part.image.width  }}

#META# IMAGE HEIGHT: {{ part.image.height  }}


#META#Header#End#

{% for line in lines %}~~{{ line.content }}
{% endfor %}