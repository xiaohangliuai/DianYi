# Third-party data notices

## ECDICT

DianYi downloads ECDICT 1.0.28 from its upstream repository and retains the
upstream MIT license beside the installed database. DianYi does not
redistribute the dataset in this repository.

- Source: <https://github.com/skywind3000/ECDICT>
- Pinned commit: `8defb761f7c7ad1818ca94290a1844d7b33d6b23`

## Piper and Lessac voice

DianYi launches a separately installed local Piper process for pronunciation.
Voice setup downloads the runtime and model; neither is redistributed in this
Git repository. Runtime packages retain their license files in the private
environment.

- Piper 1.8.0 (GPL-3.0): <https://github.com/OHF-Voice/piper1-gpl/tree/v1.8.0>
- Voice: `en_US-lessac-medium`, 22,050 Hz, one US English speaker.
- Pinned voice repository revision: `c10ece1aade47bb51c153c893d14e5bf8e5b7117`.
- Model card: <https://huggingface.co/rhasspy/piper-voices/blob/c10ece1aade47bb51c153c893d14e5bf8e5b7117/en/en_US/lessac/medium/MODEL_CARD>
- The upstream model card references the Lessac Blizzard 2013 training dataset
  and its license: <https://www.cstr.ed.ac.uk/projects/blizzard/2013/lessac_blizzard2013/license.html>.
  Do not assume all Piper voices have the same terms. The upstream model card
  is retained beside the installed voice. Training audio is not downloaded.

Piper's bundled eSpeak NG data is required for text-to-phoneme conversion;
Piper generates the audible voice using the Lessac neural model.
