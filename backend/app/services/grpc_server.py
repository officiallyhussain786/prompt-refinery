import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from concurrent import futures
import grpc

from app.services import refine_pb2
from app.services import refine_pb2_grpc
from app.rag.retriever import get_retriever
from app.services.refiner import get_refiner


class PromptRefinerServicer(refine_pb2_grpc.PromptRefinerServicer):
    def __init__(self):
        self.retriever = get_retriever()
        self.refiner = get_refiner()

    def RefinePrompt(self, request, context):
        patterns = self.retriever.search(
            request.original_prompt, request.refinement_mode
        )

        result = self.refiner.refine(
            request.original_prompt, request.refinement_mode, patterns
        )

        return refine_pb2.RefineResponse(
            refined_prompt=result["refined_prompt"],
            intent_detected=result["intent"],
            original_score=result["original_score"],
            refined_score=result["refined_score"],
            improvements=result["improvements"],
        )


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    refine_pb2_grpc.add_PromptRefinerServicer_to_server(PromptRefinerServicer(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    print("gRPC Server started on port 50051")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()