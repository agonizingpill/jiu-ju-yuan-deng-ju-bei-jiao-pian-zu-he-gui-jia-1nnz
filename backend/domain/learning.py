import numpy as np
from sklearn.decomposition import NMF

def calculate(data):
    model=NMF(n_components=2,init='nndsvda',max_iter=1000,random_state=24)
    model.fit(data['history'])
    observation=np.asarray([data['target']['bands']])
    coeff=model.transform(observation)
    approximate=coeff@model.components_
    return {'coefficients':coeff[0].round(4).tolist(),'dominant':int(coeff.argmax())+1,
            'mean_error':round(float(np.mean(abs(approximate-observation))),5),'references':len(data['history'])}
