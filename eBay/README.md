# Ebay data

**Source:** https://www.nber.org/research/data/best-offer-sequential-bargaining

* Go to [nber](https://www.nber.org/research/data/best-offer-sequential-bargaining) and download the file [anon_bo_lists.csv.gz](http://data.nber.org/data/bargaining/anon_bo_lists.csv.gz).
* Unzip it (warning: the file is *very* large, containing 98 million product listings with many string variables).
* Run the notebook `materialize.ipynb`.
* **Output:** `ebay_smaller.parquet`: a much smaller dataset around 150mb in size. 

## Description 

The dataset is extremely rich and can be used to explore many aspects of bargaining or "auctions" (although it is not strictly speaking an auction). A row is a listing with an initial price, a final price, a reference price for the product, the product category, some information on the seller (number of previous listings and an ID), etc.
