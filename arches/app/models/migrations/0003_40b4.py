# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2017-04-25 11:36
from __future__ import unicode_literals

import os
import uuid
import django.db.models.deletion
import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
from django.core import management
from arches.app.models.models import GraphModel
from arches.app.models.system_settings import settings
from arches.app.search.mappings import prepare_search_index, delete_search_index

def forwards_func(apps, schema_editor):
    # We get the model from the versioned app registry;
    # if we directly import it, it'll be the wrong version

    delete_search_index()
    for graphid in GraphModel.objects.filter(isresource=True).values_list('graphid', flat=True):
        prepare_search_index(str(graphid), create=True)

    settings_data_file = 'Arches_System_Settings.json'
    local_settings_available = os.path.isfile(os.path.join(settings.ROOT_DIR, 'db', 'system_settings', 'Arches_System_Settings_Local.json'))

    if local_settings_available == True:
        settings_data_file = 'Arches_System_Settings_Local.json'

    management.call_command('es', operation='index_resources')
    management.call_command('packages', operation='import_graphs', source=os.path.join(settings.ROOT_DIR, 'db', 'system_settings', 'Arches_System_Settings_Model.json'))
    management.call_command('packages', operation='import_business_data', source=os.path.join(settings.ROOT_DIR, 'db', 'system_settings', settings_data_file), overwrite='overwrite')

def reverse_func(apps, schema_editor):
    GraphModel.objects.get(graphid=settings.SYSTEM_SETTINGS_RESOURCE_MODEL_ID).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('models', '0002_40b4'),
    ]

    operations = [
        migrations.RunSQL("""
            UPDATE d_data_types
                SET issearchable = true,
                    configcomponent = 'views/graph/datatypes/string',
                    configname = 'string-datatype-config'
                WHERE datatype = 'string';
            UPDATE d_data_types
                SET issearchable = true,
                    configcomponent = 'views/graph/datatypes/number',
                    configname = 'number-datatype-config'
                WHERE datatype = 'number';
            UPDATE d_data_types
                SET issearchable = true,
                    configcomponent = 'views/graph/datatypes/boolean',
                    configname = 'boolean-datatype-config'
                WHERE datatype = 'boolean';
            UPDATE d_data_types
                SET issearchable = true,
                    configcomponent = 'views/graph/datatypes/domain-value',
                    configname = 'domain-value-datatype-config'
                WHERE datatype = 'domain-value';
            UPDATE d_data_types
                SET issearchable = true,
                    configcomponent = 'views/graph/datatypes/concept',
                    configname = 'concept-datatype-config'
                WHERE datatype = 'concept';
            UPDATE d_data_types
                SET issearchable = true,
                    configcomponent = 'views/graph/datatypes/date',
                    configname = 'date-datatype-config'
                WHERE datatype = 'date';
        """, """
            UPDATE d_data_types
                SET issearchable = false,
                    configcomponent = NULL,
                    configname = NULL
                WHERE datatype = 'string';
            UPDATE d_data_types
                SET issearchable = false,
                    configcomponent = NULL,
                    configname = NULL
                WHERE datatype = 'number';
            UPDATE d_data_types
                SET issearchable = false,
                    configcomponent = NULL,
                    configname = NULL
                WHERE datatype = 'boolean';
            UPDATE d_data_types
                SET issearchable = false,
                    configcomponent = NULL,
                    configname = NULL
                WHERE datatype = 'domain-value';
            UPDATE d_data_types
                SET issearchable = false,
                    configcomponent = NULL,
                    configname = NULL
                WHERE datatype = 'concept';
            UPDATE d_data_types
                SET issearchable = false,
                    configcomponent = NULL,
                    configname = NULL
                WHERE datatype = 'date';
        """),

        migrations.RunSQL("""
            INSERT INTO iiif_manifests(id, url) VALUES (public.uuid_generate_v1mc(), 'https://data.getty.edu/museum/api/iiif/249995/manifest.json');
        """, """
            DELETE FROM public.iiif_manifests WHERE url = 'https://data.getty.edu/museum/api/iiif/249995/manifest.json';
        """),
        migrations.RunSQL("""
            INSERT INTO public.relations(relationid, conceptidfrom, conceptidto, relationtype) VALUES (public.uuid_generate_v1mc(), '00000000-0000-0000-0000-000000000004', '00000000-0000-0000-0000-000000000007', 'narrower') ON CONFLICT DO NOTHING;
        """,
        """
            DELETE FROM public.relations WHERE conceptidfrom = '00000000-0000-0000-0000-000000000004' AND conceptidto = '00000000-0000-0000-0000-000000000007' AND relationtype = 'narrower';
        """),
        migrations.RunSQL("""
            INSERT INTO widgets(widgetid, name, component, datatype, defaultconfig)
                VALUES ('10000000-0000-0000-0000-000000000022', 'iiif-widget', 'views/components/widgets/iiif', 'iiif-drawing', '{
                        "placeholder": "",
                        "options": [],
                        "nameLabel": "Name",
                        "typeLabel": "Type"
                    }'
                );
            INSERT INTO widgets(widgetid, name, component, datatype, defaultconfig) VALUES ('10000000-0000-0000-0000-000000000020', 'csv-chart-widget', 'views/components/widgets/csv-chart', 'csv-chart-json', '{"acceptedFiles": "", "maxFilesize": "200"}');
            INSERT INTO d_data_types VALUES ('csv-chart-json', 'fa fa-line-chart', 'datatypes.py', 'CSVChartJsonDataType', null, null, null, FALSE, '10000000-0000-0000-0000-000000000020');
            INSERT INTO d_data_types VALUES ('iiif-drawing', 'fa fa-file-code-o', 'datatypes.py', 'IIIFDrawingDataType', '{"rdmCollection": null}', 'views/graph/datatypes/concept', 'concept-datatype-config', FALSE, '10000000-0000-0000-0000-000000000022');
            UPDATE d_data_types SET (modulename, classname) = ('datatypes.py', 'DomainDataType') WHERE datatype = 'domain-value';
            UPDATE d_data_types SET (modulename, classname) = ('datatypes.py', 'DomainListDataType') WHERE datatype = 'domain-value-list';
            """,
            """
            DELETE FROM d_data_types WHERE datatype = 'iiif-drawing';
            DELETE FROM d_data_types WHERE datatype = 'csv-chart-json';
            DELETE FROM widgets WHERE widgetid = '10000000-0000-0000-0000-000000000020';
            DELETE from widgets WHERE widgetid = '10000000-0000-0000-0000-000000000022';
            UPDATE d_data_types SET (modulename, classname) = ('concept_types.py', 'ConceptDataType') WHERE datatype = 'domain-value';
            UPDATE d_data_types SET (modulename, classname) = ('concept_types.py', 'ConceptListDataType') WHERE datatype = 'domain-value-list';
        """),
        ## the following command has to be run after the previous RunSQL commands that update the domain datatype values
        migrations.RunPython(forwards_func, reverse_func),
    ]
