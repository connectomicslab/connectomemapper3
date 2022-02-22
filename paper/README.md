## Hosting the paper of Connectome Mapper 3

Content of the paper can be found in the ``paper.md`` markdown file, and the citations used
are referenced in the ``paper.bib`` bibtex file, the format of the Journal of Open-Source Software.

For convenience, the PDF of the paper can be built locally with Docker by running the following:

```bash
sh buid_paper_docker.sh
```

which will execute the ``openjournals/paperdraft`` Docker image and output the ``paper.pdf`` file.

Original `SVG` files used to generated the `PNG` illustrations of the paper in `PNG` 
can be found in the ``svg/`` folder.
