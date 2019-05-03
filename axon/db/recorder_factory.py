from axon.db.recorder import WaveFrontRecorder, SqlDbRecorder
from axon.common import config as conf
from axon.common import consts


class RecorderFactory(object):

    @classmethod
    def get_recorder(cls):
        def get_wf_recorder():
            if conf.WAVEFRONT_PROXY_ADDRESS is not None:
                server = conf.WAVEFRONT_PROXY_ADDRESS
                proxy = True
                token = None
            else:
                server = conf.WAVEFRONT_SERVER_ADDRESS
                proxy = False
                token = conf.WAVEFRONT_SERVER_API_TOKEN
            return WaveFrontRecorder(server, proxy, token)

        if conf.RECORDER and conf.RECORDER.lower() == consts.WAVEFRONT:
            return get_wf_recorder()
        else:
            return SqlDbRecorder()
