This multi-resolution parcellation was first used in:

Hagmann P, Cammoun L, Gigandet X, Meuli R, Honey CJ, et al. 2008 Mapping the Structural Core of Human Cerebral Cortex. PLoS Biol 6(7): e159. doi:10.1371/journal.pbio.0060159 
http://www.plosbiology.org/article/info:doi/10.1371/journal.pbio.0060159


Please, refer to the following article for technical details:

Cammoun L, Gigandet X, Meskaldji D, Thiran JP, Sporns O, et al. 2012 Mapping the Human Connectome at Multiple Scales with Diffusion Spectrum MRI. J Neurosci Methods 203(2): 386-397
http://www.sciencedirect.com/science/article/pii/S0165027011005991


With the release of Freesurfer 5.0, the parcellation was recreated and includes the insula.

With the release of Freesurfer 6.0.1 and the development of multiscalbrainparcellator and CMP3,
  the parcellation was recreated with the generation of .annot files as follows:

1. The right hemisphere labels were projected in the left hemisphere to create a symmetric version of the multiscale cortical parcellation proposed by Cammoun.
2. For scale 1, the boundaries of the projected regions over the left hemisphere were matched to the boundaries of the original parcellation for the left hemisphere.
3. This transformation was applied for the rest of the scales.
