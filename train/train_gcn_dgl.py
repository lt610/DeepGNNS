import sys
sys.path.append('../')
import random
import numpy as np
import torch as th
import argparse
import time
import torch.nn.functional as F
from train.early_stopping import EarlyStopping
from train.metrics import evaluate_acc_loss
from nets.gcn_dgl_net import GCNDGLNet
from utils.data_mine import load_data_default
import torch as th
import numpy as np


def set_seed(seed=9699):
    random.seed(seed)
    np.random.seed(seed)
    th.manual_seed(seed)
    th.cuda.manual_seed(seed)
    # th.backends.cudnn.deterministic = True
    # th.backends.cudnn.benchmark = False


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', type=str, default='citeseer')
    parser.add_argument('--num_hidden', type=int, default=64)
    parser.add_argument('--num_layers', type=int, default=3)

    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--learn_rate', type=float, default=1e-2)
    parser.add_argument('--weight_decay', type=float, default=0)
    parser.add_argument('--num_epochs', type=int, default=500)
    parser.add_argument('--patience', type=int, default=100)
    args = parser.parse_args()

    graph, features, labels, train_mask, val_mask, test_mask, num_feats, num_classes = load_data_default(args.dataset)
    model = GCNDGLNet(num_feats, num_classes, args.num_hidden, args.num_layers)

    # set_seed(args.seed)

    optimizer = th.optim.Adam(model.parameters(), lr=args.learn_rate, weight_decay=args.weight_decay)
    early_stopping = EarlyStopping(args.patience, file_name='tmp')

    device = th.device("cuda:0" if th.cuda.is_available() else "cpu")
    graph = graph.to(device)
    features = features.to(device)
    labels = labels.to(device)
    train_mask = train_mask.to(device)
    val_mask = val_mask.to(device)
    test_mask = test_mask.to(device)
    print(model)
    model = model.to(device)

    dur = []
    for epoch in range(args.num_epochs):
        if epoch >= 3:
            t0 = time.time()
        model.train()
        logits = model(graph, features)
        logp = F.log_softmax(logits, 1)
        loss = F.nll_loss(logp[train_mask], labels[train_mask])
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        if epoch >= 3:
            dur.append(time.time() - t0)
        train_loss, train_acc = evaluate_acc_loss(model, graph, features, labels, train_mask)
        val_loss, val_acc = evaluate_acc_loss(model, graph, features, labels, val_mask)
        print("Epoch {:05d} | Train Loss {:.4f} | Train Acc {:.4f} | Val Loss {:.4f} | Val Acc {:.4f} | Time(s) {:.4f}".
              format(epoch, train_loss, train_acc, val_loss, val_acc, np.mean(dur)))
        early_stopping(-val_loss, model)
        if early_stopping.is_stop:
            print("Early stopping")
            model.load_state_dict(early_stopping.load_checkpoint())
            break
    train_loss, train_acc = evaluate_acc_loss(model, graph, features, labels, train_mask)
    val_loss, val_acc = evaluate_acc_loss(model, graph, features, labels, val_mask)
    test_loss, test_acc = evaluate_acc_loss(model, graph, features, labels, test_mask)
    print("Train Loss {:.4f} | Train Acc {:.4f}".format(train_loss, train_acc))
    print("Val Loss {:.4f} | Val Acc {:.4f}".format(val_loss, val_acc))
    print("Test Loss {:.4f} | Test Acc {:.4f}".format(test_loss, test_acc))
