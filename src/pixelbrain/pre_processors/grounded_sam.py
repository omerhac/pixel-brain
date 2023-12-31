from typing import List
from pixelbrain.pipeline import Preprocessor
import torch
from torchvision import transforms


class GroundedSAMPreprocessor(Preprocessor):
    def __init__(self) -> None:
        self._transforms = transforms.Compose([
            transforms.ToPILImage()
        ])
    def __call__(self, image_list: List[torch.Tensor]) -> List[torch.Tensor]:
        return [self._transforms(image) for image in image_list]