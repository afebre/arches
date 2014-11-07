'''
ARCHES - a program developed to inventory and manage immovable cultural heritage.
Copyright (C) 2013 J. Paul Getty Trust and World Monuments Fund

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
'''

import uuid
from django.conf import settings
from django.db import transaction, IntegrityError
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_exempt
from django.template import RequestContext
from django.shortcuts import render_to_response
from arches.app.models import models
from arches.app.models.concept import Concept, ConceptValue, CORE_CONCEPTS
from arches.app.search.search_engine_factory import SearchEngineFactory
from arches.app.search.elasticsearch_dsl_builder import Bool, Match, Query, Nested, Terms, GeoShape, Range, SimpleQueryString
from arches.app.utils.betterJSONSerializer import JSONSerializer, JSONDeserializer
from arches.app.utils.JSONResponse import JSONResponse
from arches.app.utils.skos import SKOSWriter

def rdm(request, conceptid):
    lang = request.GET.get('lang', 'en-us')    
    
    languages = models.DLanguages.objects.all()
    concept_schemes = Concept.get_scheme_collections(include=['label'])
    concept_scheme_labels = [concept.get_preflabel(lang=lang) for concept in concept_schemes]

    return render_to_response('rdm.htm', {
            'main_script': 'rdm',
            'active_page': 'RDM',
            'languages': languages,
            'conceptid': conceptid,
            'concept_schemes': concept_scheme_labels
        }, context_instance=RequestContext(request))

@csrf_exempt
def concept(request, conceptid):
    f = request.GET.get('f', 'json')
    lang = request.GET.get('lang', 'en-us')
    pretty = request.GET.get('pretty', False)

    if request.method == 'GET':

        include_subconcepts = request.GET.get('include_subconcepts', 'true') == 'true'
        include_parentconcepts = request.GET.get('include_parentconcepts', 'true') == 'true'
        include_relatedconcepts = request.GET.get('include_relatedconcepts', 'true') == 'true'
        emulate_elastic_search = request.GET.get('emulate_elastic_search', 'false') == 'true'
        fromdb = request.GET.get('fromdb', 'false') == 'true'
        depth_limit = request.GET.get('depth_limit', None)
        mode = request.GET.get('mode', 'scheme')

        if f == 'html':
            fromdb = True
            depth_limit = 1
            if conceptid == None:
                return render_to_response('views/rdm/concept-report.htm', {
                    'lang': lang,
                    'concept_count': models.Concepts.objects.filter(nodetype='Concept').count(),
                    'collection_count': models.Concepts.objects.filter(nodetype='Collection').count(),
                    'scheme_count': models.Concepts.objects.filter(nodetype='ConceptScheme').count(),
                    'entitytype_count': models.Concepts.objects.filter(nodetype='EntityType').count(),
                    'default_report': True
                }, context_instance=RequestContext(request))

        if f == 'skos':
            fromdb = True

        if fromdb:
            ret = []
            labels = []
            concept_graph = Concept().get(id=conceptid, include_subconcepts=include_subconcepts, 
                include_parentconcepts=include_parentconcepts, include_relatedconcepts=include_relatedconcepts,
                depth_limit=depth_limit, up_depth_limit=None)

            if f == 'html':
                print concept_graph.nodetype
                if concept_graph.nodetype != 'Collection':
                    languages = models.DLanguages.objects.all()
                    valuetypes = models.ValueTypes.objects.all()
                    relationtypes = models.DRelationtypes.objects.all()
                    prefLabel = concept_graph.get_preflabel(lang=lang).value
                    for value in concept_graph.values:
                        if value.category == 'label':
                            labels.append(value)
                    direct_parents = [parent.get_preflabel(lang=lang) for parent in concept_graph.parentconcepts]
                    return render_to_response('views/rdm/concept-report.htm', {
                        'lang': lang,
                        'prefLabel': prefLabel,
                        'labels': labels,
                        'concept': concept_graph,
                        'languages': languages,
                        'valuetype_labels': valuetypes.filter(category='label'),
                        'valuetype_notes': valuetypes.filter(category='note'),
                        'valuetype_related_values': valuetypes.filter(category='undefined'),
                        'parent_relations': relationtypes.filter(category='Semantic Relations').exclude(relationtype='related'),
                        'concept_paths': concept_graph.get_paths(lang=lang),
                        'graph_json': JSONSerializer().serialize(concept_graph.get_node_and_links(lang=lang)),
                        'direct_parents': direct_parents
                    }, context_instance=RequestContext(request))

                else:
                    languages = models.DLanguages.objects.all()
                    valuetypes = models.ValueTypes.objects.all()
                    relationtypes = models.DRelationtypes.objects.all()
                    prefLabel = concept_graph.get_preflabel(lang=lang).value
                    for value in concept_graph.values:
                        if value.category == 'label':
                            labels.append(value)
                    direct_parents = [parent.get_preflabel(lang=lang) for parent in concept_graph.parentconcepts]
                    return render_to_response('views/rdm/entitytype-report.htm', {
                        'lang': lang,
                        'prefLabel': prefLabel,
                        'labels': labels,
                        'concept': concept_graph,
                        'languages': languages,
                        'valuetype_labels': valuetypes.filter(category='label'),
                        'valuetype_notes': valuetypes.filter(category='note'),
                        'valuetype_related_values': valuetypes.filter(category='undefined'),
                        'parent_relations': relationtypes.filter(category='Semantic Relations').exclude(relationtype='related'),
                        'concept_paths': concept_graph.get_paths(lang=lang),
                        'graph_json': JSONSerializer().serialize(concept_graph.get_node_and_links(lang=lang)),
                        'direct_parents': direct_parents
                    }, context_instance=RequestContext(request))

            if f == 'skos':
                skos = SKOSWriter()
                return HttpResponse(skos.write(concept_graph, format="pretty-xml"), content_type="application/xml")

            if emulate_elastic_search:
                ret.append({'_type': id, '_source': concept_graph})
            else:
                ret.append(concept_graph)       

            if emulate_elastic_search:
                ret = {'hits':{'hits':ret}} 

            return JSONResponse(ret, indent=4 if pretty else None)   

        else:
            se = SearchEngineFactory().create()
            return JSONResponse(se.search('', index='concept', search_field='value', use_wildcard=True))


    if request.method == 'POST':
        if len(request.FILES) > 0:
            value = models.FileValues(valueid = str(uuid.uuid4()), value = request.FILES.get('file', None), conceptid_id = conceptid, valuetype_id = 'image', datatype = 'text', languageid_id = 'en-us')
            value.save()

            return JSONResponse(value)
        else:
            json = request.body

            if json != None:
                data = JSONDeserializer().deserialize(json)
                
                with transaction.atomic():
                    concept = Concept(data)
                    concept.save()

                    if conceptid not in CORE_CONCEPTS:
                        concept.index()

                    return JSONResponse(concept)


    if request.method == 'DELETE':
        json = request.body
        if json != None:
            data = JSONDeserializer().deserialize(json)
            
            with transaction.atomic():
                concept = Concept(data)

                if concept.id not in CORE_CONCEPTS:
                    concept.delete_index()                
                concept.delete()

                return JSONResponse(concept)

    return HttpResponseNotFound()


@csrf_exempt
def manage_parents(request, conceptid):
    #  need to check user credentials here

    if request.method == 'POST':
        json = request.body
        if json != None:
            data = JSONDeserializer().deserialize(json)
            
            with transaction.atomic():
                if len(data['deleted']) > 0:
                    concept = Concept({'id':conceptid})
                    for deleted in data['deleted']:
                        concept.addparent(deleted)  
    
                    concept.delete()
                
                if len(data['added']) > 0:
                    concept = Concept({'id':conceptid})
                    for added in data['added']:
                        concept.addparent(added)   
            
                    concept.save()

                return JSONResponse(data)

    else:
        HttpResponseNotAllowed(['POST'])

    return HttpResponseNotFound()

@csrf_exempt
def confirm_delete(request, conceptid):
    concepts_to_delete = [concept.value for concept in Concept.gather_concepts_to_delete(conceptid)]

    #return JSONResponse(concepts_to_delete)
    return HttpResponse('<ul><li>' + '<li>'.join(concepts_to_delete) + '</ul>')

@csrf_exempt
def search(request):
    se = SearchEngineFactory().create()
    searchString = request.GET['q']
    query = Query(se, start=0, limit=100)
    phrase = Match(field='value', query=searchString.lower(), type='phrase_prefix')
    query.add_query(phrase)
    results = query.search(index='concept_labels')

    cached_scheme_names = {}
    for result in results['hits']['hits']:
        # first look to see if we've already retrieved the scheme name
        # else look up the scheme name with ES and cache the result
        if result['_type'] in cached_scheme_names:
            result['_type'] = cached_scheme_names[result['_type']]
        else:
            query = Query(se, start=0, limit=100)
            phrase = Match(field='conceptid', query=result['_type'], type='phrase')
            query.add_query(phrase)
            scheme = query.search(index='concept_labels')
            for label in scheme['hits']['hits']:
                if label['_source']['type'] == 'prefLabel':
                    cached_scheme_names[result['_type']] = label['_source']['value']
                    result['_type'] = label['_source']['value']
    return JSONResponse(results)

def concept_tree(request):
    conceptid = request.GET.get('node', None)
    concepts = Concept({'id': conceptid}).concept_tree()
    return JSONResponse(concepts, indent=4)
