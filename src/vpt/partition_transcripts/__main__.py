from vpt.partition_transcripts.run_partition_transcripts import main_partition_transcripts
from vpt.partition_transcripts.cmd_args import parse_args

if __name__ == '__main__':
    main_partition_transcripts(parse_args())
