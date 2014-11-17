collectd-bcache-plugin
====================

This is a collectd plugin which runs under the Python plugin to collect metrics from BCACHE 


Configure
=========

Add configuration to collectd-bcache-plugin into <Plugin python> section at collectd.conf<br>

<pre>
<Plugin python><br>
    ModulePath "/usr/share/collectd-plugins"
    Encoding "utf-8"
    LogTraces true
    Interactive false
    Import "bcache"
    <module bcache>
        Verbose true
    </module>
</Plugin>
</pre>

Graphite
========

For perfect integration with plugin write_graphite, we need change parameter EscapeCharacter in section Cabon to

EscapeCharacter "."


