"""Image transforms built from the training config.

Beans have no canonical orientation, so flips and full rotation are safe and
useful augmentations. Normalisation uses ImageNet statistics to match the
pretrained backbones.
"""

from __future__ import annotations

from torchvision import transforms

_IMAGENET_MEAN = (0.485, 0.456, 0.406)
_IMAGENET_STD = (0.229, 0.224, 0.225)


def build_transforms(image_size: int, aug_cfg=None, *, train: bool):
    """Compose a torchvision transform pipeline.

    `aug_cfg` is the `train.augmentation` config block; ignored when `train`
    is False (validation/test use a plain resize).
    """
    steps: list = []

    if train and aug_cfg:
        if aug_cfg.get("random_resized_crop", False):
            steps.append(transforms.RandomResizedCrop(image_size, scale=(0.7, 1.0)))
        else:
            steps.append(transforms.Resize((image_size, image_size)))
        if aug_cfg.get("hflip", False):
            steps.append(transforms.RandomHorizontalFlip())
        if aug_cfg.get("vflip", False):
            steps.append(transforms.RandomVerticalFlip())
        rotation = aug_cfg.get("rotation_deg", 0)
        if rotation:
            steps.append(transforms.RandomRotation(rotation))
        jitter = aug_cfg.get("color_jitter", 0)
        if jitter:
            steps.append(transforms.ColorJitter(jitter, jitter, jitter))
    else:
        steps.append(transforms.Resize((image_size, image_size)))

    steps.append(transforms.ToTensor())
    steps.append(transforms.Normalize(_IMAGENET_MEAN, _IMAGENET_STD))
    return transforms.Compose(steps)
