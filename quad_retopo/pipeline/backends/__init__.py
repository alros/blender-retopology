from .quadriflow import QuadriFlowBackend

BACKENDS = {
    QuadriFlowBackend.id: QuadriFlowBackend,
}


def get_backend(backend_id):
    return BACKENDS[backend_id]()
