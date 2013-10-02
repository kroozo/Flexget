from __future__ import unicode_literals, division, absolute_import
from difflib import SequenceMatcher
import logging

from flexget import plugin
from flexget.event import event

log = logging.getLogger('urlrewrite_search')


class PluginSearch(object):
    """
    Search entry from sites. Accepts list of known search plugins, list is in priority order.
    Once hit has been found no more searches are performed. Should be used only when
    there is no other way to get working download url, ie. when input plugin does not provide
    any downloadable urls.

    Example::

      urlrewrite_search:
        - newtorrents
        - piratebay

    .. note:: Some url rewriters will use search plugins automatically if entry url
              points into a search page.
    """

    def validator(self):
        from flexget import validator
        search = validator.factory('list')
        names = []
        for p in plugin.get_plugins_by_group('search'):
            # If the plugin has a validator, get it's validator and make it a
            # child of the search plugins
            if not hasattr(p.instance, 'validator'):
                # Create choice validator for plugins without validators later
                names.append(p.name)
            else:
                plugin_validator = p.instance.validator()
                if isinstance(plugin_validator, validator.Validator):
                    search.accept('dict').accept(plugin_validator, key=p.name)
                else:
                    log.error("plugin %s has a validator method, but does not "
                              "return a validator instance when called with "
                              "search plugin." % p.name)
        search.accept('choice').accept_choices(names)
        return search

    # Run before main urlrewriting
    @plugin.priority(130)
    def on_task_urlrewrite(self, task, config):
        # no searches in unit test mode
        if task.manager.unit_test:
            return

        plugins = {}
        for p in plugin.get_plugins_by_group('search'):
            plugins[p.name] = p.instance

        # search accepted
        for entry in task.accepted:
            # loop through configured searches
            for name in config:
                search_config = None
                if isinstance(name, dict):
                    # assume the name is the first/only key in the dict.
                    name, search_config = name.items()[0]
                log.verbose('Searching `%s` from %s' % (entry['title'], name))
                try:
                    results = plugins[name].search(entry, search_config)
                    matcher = SequenceMatcher(a=entry['title'])
                    for result in sorted(results, key=lambda e: e.get('search_sort'), reverse=True):
                        matcher.set_seq2(result['title'])
                        if matcher.ratio() > 0.9:
                            log.debug('Found url: %s', result['url'])
                            entry['url'] = result['url']
                            break
                    else:
                        continue
                    break
                except (plugin.PluginError, plugin.PluginWarning) as pw:
                    log.verbose('Failed: %s' % pw.value)
                    continue

            # Search failed
            else:
                # If I don't have a URL, doesn't matter if I'm immortal...
                entry['immortal'] = False
                entry.reject('search failed')


@event('plugin.register')
def register_plugin():
    plugin.register(PluginSearch, 'urlrewrite_search', api_ver=2)
