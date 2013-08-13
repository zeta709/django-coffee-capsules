from itertools import chain

from django import forms
from django.forms.util import flatatt
from django.utils import formats
from django.utils.html import conditional_escape
from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe


# References:
# "class Select(Widget)" and "class Input(Widget)"
# in /usr/lib/python2.7/dist-packages/django/forms/widgets.py
class SelectedReadonly(forms.widgets.Widget):
    allow_multiple_selected = False

    def __init__(self, attrs=None, choices=()):
        super(SelectedReadonly, self).__init__(attrs)
        self.choices = list(choices)

    def _format_value(self, value):
        if self.is_localized:
            return formats.localize_input(value)
        return value

    def render(self, name, value, attrs=None, choices=()):
        if value is None:
            value = ''
        final_attrs = self.build_attrs(attrs, type='hidden', name=name)
        if value != '':
            final_attrs['value'] = force_unicode(self._format_value(value))
        output = [u'<input%s /><span>' % flatatt(final_attrs)]
        selected_option = self.render_options(choices, [value])
        if selected_option:
            output.append(selected_option)
        output.append(u'</span>')
        return mark_safe(u'\n'.join(output))

    def render_option(self, selected_choices, option_value, option_label):
        option_value = force_unicode(option_value)
        if option_value in selected_choices:
            if not self.allow_multiple_selected:
                selected_choices.remove(option_value)
            return u'%s' % (conditional_escape(force_unicode(option_label)))
        else:
            return u''

    def render_options(self, choices, selected_choices):
        selected_choices = set(force_unicode(v) for v in selected_choices)
        output = []
        for option_value, option_label in chain(self.choices, choices):
            if isinstance(option_label, (list, tuple)):
                for option in option_label:
                    rendered_option = self.render_option(selected_choices,
                                                         *option)
                    if rendered_option != '':
                        output.append(rendered_option)
            else:
                rendered_option = self.render_option(selected_choices,
                                                     option_value,
                                                     option_label)
                if rendered_option != '':
                    output.append(rendered_option)
        return u'\n'.join(output)
