import typing

import torch
import torch.nn as nn

from pyraug.models.nn import *


class Encoder_MLP(Base_Encoder):
    def __init__(self, args: dict):
        Base_Encoder.__init__(self)

        if args.input_dim is None:
            raise AttributeError("No input dimension provided !"
            "'input_dim' parameter of ModelConfig instance must be set to 'data_shape' where "
            "the shape of the data is [mini_batch x data_shape]. Unable to build encoder " 
            "automatically")

        self.input_dim = args.input_dim
        self.latent_dim = args.latent_dim

        self.layers = nn.Sequential(nn.Linear(args.input_dim, 500), nn.ReLU())
        self.mu = nn.Linear(500, self.latent_dim)
        self.std = nn.Linear(500, self.latent_dim)

    def forward(self, x):
        out = self.layers(x.reshape(-1, self.input_dim))
        return self.mu(out), self.std(out)


class Decoder_MLP(Base_Decoder):
    def __init__(self, args: dict):
        Base_Decoder.__init__(self)

        if args.input_dim is None:
            raise AttributeError("No input dimension provided !"
            "'input_dim' parameter of ModelConfig instance must be set to 'data_shape' where "
            "the shape of the data is [mini_batch x data_shape]. Unable to build decoder" 
            "automatically")

        self.layers = nn.Sequential(
            nn.Linear(args.latent_dim, 500),
            nn.ReLU(),
            nn.Linear(500, args.input_dim),
            nn.Sigmoid(),
        )

    def forward(self, z):
        return self.layers(z)


class Metric_MLP(Base_Metric):
    def __init__(self, args: dict):
        Base_Metric.__init__(self)

        if args.input_dim is None:
            raise AttributeError("No input dimension provided !"
            "'input_dim' parameter of ModelConfig instance must be set to 'data_shape' where "
            "the shape of the data is [mini_batch x data_shape]. Unable to build metric " 
            "automatically")

        self.input_dim = args.input_dim
        self.latent_dim = args.latent_dim

        self.layers = nn.Sequential(nn.Linear(self.input_dim, 400), nn.ReLU())
        self.diag = nn.Linear(400, self.latent_dim)
        k = int(self.latent_dim * (self.latent_dim - 1) / 2)
        self.lower = nn.Linear(400, k)

    def forward(self, x):

        h1 = self.layers(x.reshape(-1, self.input_dim))
        h21, h22 = self.diag(h1), self.lower(h1)

        L = torch.zeros((x.shape[0], self.latent_dim, self.latent_dim)).to(x.device)
        indices = torch.tril_indices(
            row=self.latent_dim, col=self.latent_dim, offset=-1
        )

        # get non-diagonal coefficients
        L[:, indices[0], indices[1]] = h22

        # add diagonal coefficients
        L = L + torch.diag_embed(h21.exp())

        return L


class Encoder_Conv(Base_Encoder):
    def __init__(self, args):
        Base_Encoder.__init__(self)
        self.input_dim = args.input_dim
        self.latent_dim = args.latent_dim
        self.n_channels = args.n_channels

        self.layers = nn.Sequential(
            nn.Conv2d(
                self.n_channels, out_channels=32, kernel_size=3, stride=2, padding=1
            ),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.Conv2d(32, out_channels=32, kernel_size=3, stride=2, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.Conv2d(32, out_channels=32, kernel_size=3, stride=2, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
        )

        self.fc1 = nn.Sequential(nn.Linear(512, 400), nn.ReLU())

        self.mu = nn.Linear(400, self.latent_dim)
        self.std = nn.Linear(400, self.latent_dim)

    def forward(self, x):
        out = self.layers(x.reshape(-1, self.n_channels, x.shape[-2], x.shape[-1]))
        out = self.fc1(out.reshape(x.shape[0], -1))
        return self.mu(out), self.std(out)


class Decoder_Conv(Base_Decoder):
    def __init__(self, args):

        Base_Decoder.__init__(self)

        self.input_dim = args.input_dim
        self.latent_dim = args.latent_dim
        self.n_channels = args.n_channels

        self.fc1 = nn.Sequential(
            nn.Linear(self.latent_dim, 400), nn.ReLU(), nn.Linear(400, 512), nn.ReLU()
        )

        self.layers = nn.Sequential(
            nn.ConvTranspose2d(32, out_channels=32, kernel_size=3, stride=2, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.ConvTranspose2d(
                32,
                out_channels=32,
                kernel_size=3,
                stride=2,
                padding=1,
                output_padding=1,
            ),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.ConvTranspose2d(
                32, out_channels=3, kernel_size=3, stride=2, padding=1, output_padding=1
            ),
            nn.BatchNorm2d(3),
            nn.ReLU(),
        )

    def forward(self, z):
        out = self.fc1(z)
        out = self.layers(out.reshape(z.shape[0], 32, 4, 4))
        return out
