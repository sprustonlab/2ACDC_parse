from pathlib import Path
from tokenize import Name
from linear2ac.parse import parse_linear_2ac
from vr2p.gimbl.parse import parse_gimbl_log
from tqdm.notebook import tqdm
from sys import platform
import zarr
import numcodecs

import pickle

def process_vr2p_data(zarr_file):
    """Process zarr folder created by vr2p module

    Args:
        zarr_file (Path): location of zarr file/directory
    """
    with zarr.open(zarr_file.as_posix(), "r+") as f:
        # check if copy of original exists.
        if 'gimbl/vr_original/' not in f:
            f.create_group('gimbl/vr_original')
            zarr.convenience.copy_all(f['gimbl/vr'],f['gimbl/vr_original'], object_codec = numcodecs.Pickle())
        # delete current info.
        if 'gimbl/vr' in f:
            del f['gimbl/vr']
        # process per session.
        for session in tqdm(f['gimbl/vr_original'].keys(),desc='Processing session:'):
            f.require_group('gimbl/vr').create_dataset(session, 
                        data = parse_linear_2ac(f[f"gimbl/log/{session}"][()].value, f[f"gimbl/vr_original/{session}"][()]), 
                        dtype=object, object_codec = numcodecs.Pickle())

def collect_log_data(main_folder, force_reparse = False, verbose=False):
    """Gets all log data from the suppliad data paths.

    Args:
        main_folder (string):  Main data folder root. Searches for folders of pattern: 2020_01_01/1
        force_reparse (bool, optional): For reparsing of log files even if pickle file is present in folder. Defaults to False.

    Returns:
        list: List of dataframes with ouput from parse_ymaze.
    """
    vr = []
    for data_path in tqdm(find_data_paths(main_folder),desc='Parsing logs', disable = not verbose):
        # test if processed log file is already present.
        log_file = data_path/'log.pkl'
        if log_file.is_file() and not force_reparse:
            vr.append(load_log_data(log_file))
        # If not present then parse raw log file.
        else:
            # load and parse json log file.
            log_file = find_log_file(data_path)
            df, vr_session = parse_gimbl_log(log_file)
            try:
                vr_session = parse_linear_2ac(df,vr_session)
                # save.
                save_log_data(data_path/'log.pkl',vr_session) 
                # store
                vr.append(vr_session)
            except Exception as e:
                print(f"Could not parse {data_path}")
                raise
    return vr
def find_data_paths(main_folder):
    """Find data folders in main folder of format 2020_01_01/1

    Args:
        main_folder (string): Main data folder root.
    """
    main_folder = Path(main_folder)
    data_paths = list(sorted(main_folder.glob('[0-9][0-9][0-9][0-9]_[0-9][0-9]_[0-9][0-9]/[0-9]/')))
    return  data_paths

def find_log_file(data_path):
    """Find log file that is json and has year number in file name

    Args:
        data_path (Path): folder to search

    Raises:
        NameError: Could not find log file
        NameError: Found multiple possible log files

    Returns:
        Path: log file path.
    """
    log_file = list(data_path.glob('*20[0-9][0-9]*.json'))
    if len(log_file)==0:
        log_file = list(data_path.glob('Log*.json'))
    if len(log_file)==0:
        raise NameError(f'Could not find log file in {data_path}')
    if len(log_file)>1:
        raise NameError(f'Found multiple possible log files in {data_path}')
    return log_file[0]

def save_log_data(log_file,vr):
    """Save log data in folder

    Args:
        log_file (Path): log file destinations
        vr (DataFrame): parsed dataframe generated by parse_ymaze.
    """
    with open( log_file, "wb" ) as f:
        pickle.dump( vr,  f)

def load_log_data(log_file):
    """Load saved log info as generated by save_log_file.

    Args:
        log_file (Path): log file location

    Returns:
        vr (DataFrame): parsed dataframe generated by parse_ymaze.
    """
    with open(log_file,'rb') as f:
        return pickle.load(f)

def get_main_data_folder(os=None):
    if not os:
        os=platform
    main_folder = 'Tyche/vr2p datasets'
    if os == "linux" or os == "linux2":
        return Path(f'//nrs/spruston/{main_folder}')
    elif os == "darwin":
        return Path(f'smb://nrsv.hhmi.org/spruston/{main_folder}')
    elif os == "win32":
        return Path(f'//nrsv/spruston/{main_folder}')