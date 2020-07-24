.. _citing:

*********
Citing
*********

.. important::
  * If your are using the Connectome Mapper 3 in your work, please acknowledge this software and its dependencies. To help you to do so, we recommend you to use, modify to your needs, and include in your work the following text:

    `Results included in this manuscript come from the Connectome Mapper 3 version latest [1,2], a processing pipeline, written in Python which uses Nipype [3,4. It is encapsulated in a BIDS app [5] based on Docker [6] and Singularity [7] container technologies. Resampling to isotropic resolution, Desikan-Killiany brain parcellation [8], brainstem parcellation [9], and hippocampal subfields segmentation [10] were performed using FreeSurfer 6.0.1. Final parcellations were created by performing cortical brain parcellation on at 5 different scales [11], probabilistic atlas-based segmentation of the thalamic nuclei [12],and combination of all segmented structures, using in-house CMTK tools and the antsRegistrationSyNQuick tool of ANTS v2.2.0 [13.`:emphasis:

  **References**

  1. Tourbier S, Aleman-Gomez Y, Mullier E, Griffa A, Bach Cuadra M, Hagmann P (2020). connectomicslab/connectomemapper3: Connectome Mapper |release| (Version  |release|). Zenodo. http://doi.org/10.5281/zenodo.3475969.

  2. Tourbier S, Aleman-Gomez Y, Mullier E, Griffa A, Bach Cuadra M, Hagmann P (2020, June). Connectome Mapper 3: a software pipeline for multi-scale connectome mapping of multimodal MR data. 26th Annual Meeting of the Organization for Human Brain Mapping (OHBM), abstract #1174, poster #1892.

  3. Gorgolewski K, Burns CD, Madison C, Clark D, Halchenko YO, Waskom ML, Ghosh SS (2011). Nipype: a flexible, lightweight and extensible neuroimaging data processing framework in python. Front Neuroinform, vol. 5, no. 13. doi:10.3389/fninf.2011.00013.

  4. Gorgolewski KJ, Esteban O, Ellis DG, Notter MP, Ziegler E, Johnson H, Hamalainen C, Yvernault B, Burns C, Manhães-Savio A, Jarecka D, Markiewicz CJ, Salo T, Clark D, Waskom M, Wong J, Modat M, Dewey BE, Clark MG, Dayan M, Loney F, Madison C, Gramfort A, Keshavan A, Berleant S, Pinsard B, Goncalves M, Clark D, Cipollini B, Varoquaux G, Wassermann D, Rokem A, Halchenko YO, Forbes J, Moloney B, Malone IB, Hanke M, Mordom D, Buchanan C, Pauli WM, Huntenburg JM, Horea C, Schwartz Y, Tungaraza R, Iqbal S, Kleesiek J, Sikka S, Frohlich C, Kent J, Perez-Guevara M, Watanabe A, Welch D, Cumba C, Ginsburg D, Eshaghi A, Kastman E, Bougacha S, Blair R, Acland B, Gillman A, Schaefer A, Nichols BN, Giavasis S, Erickson D, Correa C, Ghayoor A, Küttner R, Haselgrove C, Zhou D, Craddock RC, Haehn D, Lampe L, Millman J, Lai J, Renfro M, Liu S, Stadler J, Glatard T, Kahn AE, Kong X-Z, Triplett W, Park A, McDermottroe C, Hallquist M, Poldrack R, Perkins LN, Noel M, Gerhard S, Salvatore J, Mertz F, Broderick W, Inati S, Hinds O, Brett M, Durnez J, Tambini A, Rothmei S, Andberg SK, Cooper G, Marina A, Mattfeld A, Urchs S, Sharp P, Matsubara K, Geisler D, Cheung B, Floren A, Nickson T, Pannetier N, Weinstein A, Dubois M, Arias J, Tarbert C, Schlamp K, Jordan K, Liem F, Saase V, Harms R, Khanuja R, Podranski K, Flandin G, Papadopoulos Orfanos D, Schwabacher I, McNamee D, Falkiewicz M, Pellman J, Linkersdörfer J, Varada J, Pérez-García F, Davison A, Shachnev D, Ghosh S (2017). Nipype: a flexible, lightweight and extensible neuroimaging data processing framework in Python. doi:10.5281/zenodo.581704.

  5. Gorgolewski KJ, Alfaro-Almagro F, Auer T, Bellec P, Capota M, Chakravarty MM, Churchill NW, Cohen AL, Craddock RC, Devenyi GA, Eklund A, Esteban O, Flandin G, Ghosh SS, Guntupalli JS, Jenkinson M, Keshavan A, Kiar G, Liem F, Raamana PR, Raffelt D, Steele CJ, Quirion P, Smith RE, Strother SC, Varoquaux G, Wang Y, Yarkoni T,  Poldrack RA (2017). BIDS apps: Improving ease of use, accessibility, and reproducibility of neuroimaging data analysis methods. PLOS Computational Biology, vol.13, no. 3, e1005209. doi:10.1371/journal.pcbi.1005209.

  6. Merkel D (2014). Docker: lightweight Linux containers for consistent development and deployment. Linux Journal, vol. 2014, no. 239. https://dl.acm.org/citation.cfm?id=2600239.2600241

  7. Kurtzer GM, Sochat V, Bauer MW (2017). Singularity: Scientific containers for mobility of compute. PLoS ONE, vol. 12, no. 5, e0177459. doi: 10.1371/journal.pone.0177459

  8. Desikan RS, Ségonne F, Fischl B, Quinn BT, Dickerson BC, Blacker D, Buckner RL, Dale AM, Maguire RP, Hyman BT, Albert MS, Killiany RJ. An automated labeling system for subdividing the human cerebral cortex on MRI scans into gyral based regions of interest. NeuroImage, vol. 31, no. 3, pp. 968-980. doi:10.1016/j.neuroimage.2006.01.021.

  9. Iglesias JE, Van Leemput K, Bhatt P, Casillas C, Dutt S, Schuff N, Truran-Sacrey D, Boxer A, Fischl B (2015). Bayesian segmentation of brainstem structures in MRI. Neuroimage, vol. 113, pp. 184-195. doi: 10.1016/j.neuroimage.2015.02.065.

  10. Iglesias JE, Augustinack JC, Nguyen K, Player CM, Player A, Wright M, Roy N, Frosch MP, McKee AC, Wald LL, Fischl B, Van Leemput K (2015). A computational atlas of the hippocampal formation using ex vivo, ultra-high resolution MRI: Application to adaptive segmentation of in vivo MRI. Neuroimage, vol. 115, July, pp. 117-137. doi: 10.1016/j.neuroimage.2015.04.042.

  11. Cammoun L, Gigandet X, Meskaldji D, Thiran JP, Sporns O, Do KQ, Maeder P, Meuli RA, Hagmann P (2012). Mapping the human connectome at multiple scales with diffusion spectrum MRI. Journal of neuroscience methods, vol. 203, no. 2, pp. 386-397. doi: 10.1016/j.jneumeth.2011.09.031.

  12. Najdenovska E, Alemán-Gómez Y, Battistella G, Descoteaux M, Hagmann P, Jacquemont S, Maeder P, Thiran JP, Fornari E, Bach Cuadra M (2018). In-vivo probabilistic atlas of human thalamic nuclei based on diffusion- weighted magnetic resonance imaging. Scientific Data, vol. 5, no. 180270. doi: 10.1038/sdata.2018.270

  13. Avants BB, Epstein CL, Grossman M, Gee JC (2008). Symmetric diffeomorphic image registration with cross-correlation: evaluating automated labeling of elderly and neurodegenerative brain. Medical Image Analysis, vol. 12, no. 1, pp. 26–41. doi:10.1016/j.media.2007.06.004.

-------
Poster
-------

* Organization for Human Brain Mapping 2020 (Abstract_; Poster_)

.. _Abstract : https://github.com/connectomicslab/cmp3-ohbm2020/blob/master/abstract/tourbier_ohbm2020_cmp3_abstract.pdf

.. _Poster : https://github.com/connectomicslab/cmp3-ohbm2020/blob/master/poster/poster_OHBM_tourbier_cmp3.pdf

.. image:: images/Tourbier_et_al_poster1892_OHBM2020.png
  :width: 888
  :align: center