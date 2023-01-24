#!/usr/bin/env nextflow

/*

This Nextflow pipeline uses the features of vpt to
perform segmentation, re-partition transcripts, and update the vzg file.

CAUTION: Because of the way NextFlow organizes output files, this pipeline
         will always overwrite existing files in the output folder.


USAGE:
/root/nextflow run main.nf -profile $profile \
--segmentation_algorithm $segmentation_algorithm \
--input_images="$input_images" \
--um_to_mosaic_file $um_to_mosaic_file \
--transcript_file $transcript_file \
--input_vzg_file $input_vzg \
--output_entity_by_gene $output_entity_by_gene \
--output_transcripts $output_transcripts \
--output_vzg $output_vzg \
--output_path $output_path \
--tile_size $tile_size \
--tile_overlap $tile_overlap \
--processes $processes

INPUTS:

$profile
        Executor parameters can be defined in the nextflow.config file. A
        "local" profile is provided that can be used as-is.

--segmentation_algorithm
        The path to the segmentation algorithm json file

--input_images
        A regular expression defining input images, as in the 
        prepare-segmentation command. For example:
        "/data/region_0/images/mosaic_(?P<stain>[\w|-]+)_z(?P<z>[0-9]+).tif"

--um_to_mosaic_file
        The path to a file with the micron to mosaic pixel transformation

--transcript_file
        The path to the detected transcript csv file

--input_vzg_file
        The path to the input vzg file that needs to be updated

--output_entity_by_gene
        The file name of the entity by gene output file

--output_transcripts
        The file name of the new entity-annotated transcripts output file

--output_vzg
        The file name of the new vzg file with updated boundaries

--output_path
        The path to which the output files should be written

--tile_size
        Integer value for the size of segmentation tiles in units of pixels

--tile_overlap
        Integer value for the overlap between of segmentation tiles
        in units of pixels

--processes
        Number of parallel processes that should be used SPECIFICALLY FOR
        the update-vzg task. Other tasks will be parallelized by NextFlow

*/

import groovy.json.JsonSlurper

params.SPECIFICATION_FILE_NAME = 'segmentation_specification.json'

process prepare_segmentation {
    /* 
    Executes the prepare-segmentation task of vpt
    */
    label 'small'

    // Each process that consumes the segmentation specification needs a separate
    // copy of the output
    output:
        path "${params.SPECIFICATION_FILE_NAME}" into spec_channel_for_prepare_file_information
        path "${params.SPECIFICATION_FILE_NAME}" into spec_channel_for_run_segmentation_on_tile
        path "${params.SPECIFICATION_FILE_NAME}" into spec_channel_for_modify_spec_json
        path "${params.SPECIFICATION_FILE_NAME}" into spec_channel_for_get_files_map

    shell:
    '''
    CMD="vpt --verbose"
    CMD+=" prepare-segmentation"
    CMD+=" --segmentation-algorithm !{params.segmentation_algorithm}"
    CMD+=" --input-images !{params.input_images}"
    CMD+=" --input-micron-to-mosaic !{params.um_to_mosaic_file}"
    CMD+=" --output-path ."
    [ ! -z "!{params.tile_size}" ] && [ "!{params.tile_size}" != "null" ] && CMD+=" --tile-size !{params.tile_size}"
    [ ! -z "!{params.tile_overlap}" ] && [ "!{params.tile_overlap}" != "null" ] && CMD+=" --tile-overlap !{params.tile_overlap}"
    CMD+=" --overwrite"

    echo "$CMD"
    $CMD
    '''
}

process prepare_file_information {
    /* 
    Provides file information for downstream tasks
    */
    label 'small'

    input:
        val spec_file from spec_channel_for_prepare_file_information

    output:
        val tile_indices into tile_index_channel mode flatten
        val tile_results_dir into tile_results_dir_channel
        val micron_geom_file_list into micron_geom_file_list_channel_for_get_files_map
        val micron_geom_file_list into micron_geom_file_list_channel

    exec:
    num_tiles = new JsonSlurper().parseText(spec_file.text).window_grid.num_tiles
    tile_indices = 0 ..< num_tiles

    output_files_json = new JsonSlurper().parseText(spec_file.text).segmentation_algorithm.output_files
    micron_geom_file_list = output_files_json.collect { it.files.micron_geometry_file }

    output_files_json = new JsonSlurper().parseText(spec_file.text).segmentation_algorithm.output_files
    assert output_files_json.size() == 1 : "Only one set of output files is supported currently"
    tile_results_dir = output_files_json[0].files.run_on_tile_dir
    if (tile_results_dir.endsWith('/')) {
        tile_results_dir = tile_results_dir[0..-2]
    }
}

process modify_spec_json {
    /* 
    Nextflow-specific modification of the segmentation specification that
    allows compile-tile-segmentation to read the collection of tile outputs
    */
    label 'small'
    publishDir "${params.output_path}"

    input:
        path spec_json_file from spec_channel_for_modify_spec_json

    output:
        path "${params.SPECIFICATION_FILE_NAME}" into spec_channel_for_compile_tile_segmentation

    script:
    INIT_VALUE = '\\"output_path\\": \\".\\"'
    SUB_VALUE = '\\"output_path\\": \\"' + params.output_path + '\\"'
    SUB_VALUE = SUB_VALUE.replaceAll("/", "\\\\/")
    """
    perl -pe "s/${INIT_VALUE}/${SUB_VALUE}/g;" ${spec_json_file} > temp.json
    mv temp.json ${params.SPECIFICATION_FILE_NAME}
    """
}

process get_files_map {
    /* 
    Organizes a file map for downstream processes
    */
    label 'small'

    input:
        val spec_json_file from spec_channel_for_get_files_map
        val micron_geom_file_list from micron_geom_file_list_channel_for_get_files_map

    output: 
        val files_map into files_map_channel_for_partition_transcripts
        val files_map into files_map_channel_for_get_filepaths

    exec:
    output_files_json = new JsonSlurper().parseText(spec_json_file.text).segmentation_algorithm.output_files
    assert output_files_json.size() == 1 : "Only one set of output files is supported currently"
    files_map = [:]
    for (micron_geom_file in micron_geom_file_list) {
        found_records = output_files_json.findAll { it.files.micron_geometry_file == micron_geom_file }
        assert found_records.size() > 0 : "Error parsing JSON: " + micron_space_geom_file + " not found"
        assert found_records.size() == 1 : "Duplicate micron geometry filename " + micron_geom_file
        output_record = found_records[0]
        files_map[micron_geom_file] = ['mosaic': output_record.files.mosaic_geometry_file,
            'entity_by_gene': params.output_entity_by_gene,
            'cell_metadata': output_record.files.cell_metadata_file]
    }
}

micron_geom_path_channel = micron_geom_file_list_channel.flatten()

process get_filepaths {
    /* 
    Organizes a file paths for downstream processes
    */
    label 'small'
    input: val files_map from files_map_channel_for_get_filepaths

    output:
        val filepath_list into filepath_channel_for_derive_cell_metadata mode flatten
        val filepath_list into filepath_channel_for_update_vzg mode flatten

    exec:
    filepath_list = files_map.collect { entry ->
        ["${params.output_path}/${entry.key}",
         "${params.output_path}/${entry.value.mosaic}",
         "${params.output_path}/${entry.value.entity_by_gene}",
         "${entry.value.cell_metadata}"]
     }
}

process run_segmentation_on_tile {
    /* 
    Executes the run-segmentation-on-tile task of vpt
    */
    label 'medium'
    publishDir "${params.output_path}"

    input:
        path spec_json_file from spec_channel_for_run_segmentation_on_tile
        val tile_index from tile_index_channel
        val tile_results_dir from tile_results_dir_channel

    output:
        path "${tile_results_dir}/${tile_index}.parquet" into segmented_tile_parquet_channel

    shell:
    '''
    CMD="vpt --verbose"
    CMD+=" run-segmentation-on-tile"
    CMD+=" --input-segmentation-parameters !{spec_json_file}"
    CMD+=" --tile-index !{tile_index}"
    CMD+=" --overwrite"

    echo "$CMD"
    $CMD
    '''
}

process compile_tile_segmentation {
    /* 
    Executes the compile-tile-segmentation task of vpt
    */
    label 'large'
    publishDir "${params.output_path}"

    input:
        path spec_json_file from spec_channel_for_compile_tile_segmentation
        path tile_result from segmented_tile_parquet_channel.collect()

    output:
        stdout compile_tile_segmentation_done_channel

    shell:
    '''
    CMD="vpt --verbose"
    CMD+=" compile-tile-segmentation"
    CMD+=" --input-segmentation-parameters !{spec_json_file}"
    CMD+=" --overwrite"

    echo "$CMD"
    $CMD
    '''
}

process partition_transcripts {
    /* 
    Executes the partition-transcripts task of vpt
    */
    label 'xlarge'
    publishDir "${params.output_path}"

    input:
        stdin compile_tile_segmentation_done_channel
        val micron_space_geom_file from micron_geom_path_channel
        val files_map from files_map_channel_for_partition_transcripts

    output:
        stdout partition_transcripts_done_channel
        path "${files_map[micron_space_geom_file].entity_by_gene}" into entity_by_gene_channel
        path "${output_transcripts_path}" optional true into output_transcripts_channel

    shell:
    expected_entity_by_gene_file = files_map[micron_space_geom_file].entity_by_gene
    '''
    CMD="vpt --verbose"
    CMD+=" partition-transcripts"
    CMD+=" --input-boundaries !{params.output_path}/!{micron_space_geom_file}"
    CMD+=" --input-transcripts !{params.transcript_file}"
    CMD+=" --output-entity-by-gene !{expected_entity_by_gene_file}"
    CMD+=" --output-transcripts !{params.output_transcripts}"
    CMD+=" --overwrite"

    echo "$CMD"
    $CMD
    '''
}

process derive_cell_metadata {
    /* 
    Executes the derive-entity-metadata task of vpt
    */
    label 'medium'
    publishDir "${params.output_path}"

    input:
        stdin partition_transcripts_done_channel
        tuple val(micron_geom), val(mosaic_geom), val(entity_by_gene), val(cell_metadata) from filepath_channel_for_derive_cell_metadata

    output:
        path "$cell_metadata" into cell_metadata_channel

    shell:
    '''
    CMD="vpt --verbose"
    CMD+=" derive-entity-metadata"
    CMD+=" --input-boundaries !{micron_geom}"
    CMD+=" --output-metadata !{cell_metadata}"
    CMD+=" --input-entity-by-gene !{entity_by_gene}"
    CMD+=" --overwrite"

    echo "$CMD"
    $CMD
    '''
}

process update_vzg {
    /* 
    Executes the update-vzg task of vpt
    */
    label 'xlarge'
    publishDir "${params.output_path}"

    input:
        tuple val(micron_geom), val(mosaic_geom), val(entity_by_gene), val(cell_metadata) from filepath_channel_for_update_vzg
        path cell_metadata_file from cell_metadata_channel

    output:
        path "${params.output_vzg}" into vzg_channel

    shell:
    '''
    CMD="vpt --verbose"
    CMD+=" --processes !{params.processes}"
    CMD+=" update-vzg"
    CMD+=" --input-boundaries !{micron_geom}"
    CMD+=" --input-vzg !{params.input_vzg_file}"
    CMD+=" --input-entity-by-gene !{entity_by_gene}"
    CMD+=" --output-vzg !{params.output_vzg}"
    CMD+=" --input-metadata !{cell_metadata_file}"
    CMD+=" --overwrite"
    
    echo "$CMD"
    $CMD
    '''
}
