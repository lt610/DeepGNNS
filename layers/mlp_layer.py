from torch import nn
from layers.gcn_layer import cal_gain, Identity


class MLPLayer(nn.Module):
    def __init__(self, in_dim, out_dim, bias=False, activation=None,
                 batch_norm=False, residual=False, dropout=0):
        super(MLPLayer, self).__init__()
        self.linear = nn.Linear(in_dim, out_dim, bias=bias)
        self.activation = activation
        self.batch_norm = batch_norm
        if batch_norm:
            self.bn = nn.BatchNorm1d(out_dim)
        self.residual = residual
        if residual:
            if in_dim != out_dim:
                self.res_fc = nn.Linear(in_dim, out_dim, bias)
            else:
                self.res_fc = Identity()
        else:
            self.register_buffer('res_fc', None)
        self.dropout = nn.Dropout(dropout)
        self.reset_parameters()

    def reset_parameters(self):
        gain = cal_gain(self.activation)
        nn.init.xavier_normal_(self.linear.weight, gain=gain)
        if isinstance(self.res_fc, nn.Linear):
            nn.init.xavier_normal_(self.res_fc.weight, gain=gain)
            if self.res_fc.bias is not None:
                nn.init.zeros_(self.res_fc.bias)

    def forward(self, g, features):
        h_pre = features
        h = self.dropout(features)
        h = self.linear(h)
        if self.batch_norm:
            h = self.bn(h)
        if self.activation:
            h = self.activation(h)
        if self.residual:
            h = h + self.res_fc(h_pre)
        return h