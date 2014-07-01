# -*- coding:utf-8 -*-

# Copyright (C) 2012 Juan Carlos Moreno <juancarlos.moreno at ecmanaged.com>
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

_CERTIFICATE_FILE = '../config/xmpp_cert.pub'

# System imports
import os
import base64

import ecagent.twlogging as log

## RSA Verify
try:
    from Crypto import PublicKey
    import Crypto.PublicKey.RSA
    from Crypto.Util import number
    from Crypto.Hash import SHA

except ImportError:
    pass


class ECVerify():
    def __init__(self, key_file=None):
        self.public_key = None

        if not key_file:
            key_file = _CERTIFICATE_FILE

        try:
            if Crypto.version_info[:2] >= (2, 2):
                _public_key = self._read_pub_key(key_file)
                if _public_key:
                    key = PublicKey.RSA.importKey(_public_key)
                    self.public_key = key.publickey()

        except:
            pass

        if not self.public_key:
            log.warn('PyCrypto not available or version is < 2.2: Please upgrade: http://www.pycrypto.org/')

    def signature(self, message):
        if self.public_key:
            if not self._verify_message(message):
                log.critical('[RSA CHECK: Failed] Command from %s has bad signature (Ignored)' % message.from_)
                del message
                return False

        del message
        return True

    def _read_pub_key(self, key_file):
        log.debug('Reading public certificate')
        public_key = None
        try:
            cert_file = os.path.join(os.path.dirname(__file__), key_file)
            if os.path.isfile(cert_file):
                f = open(cert_file, 'r')
                public_key = f.read()
                f.close()
                del f

        except:
            log.critical("Unable to read certificate file")

        del key_file
        return public_key

    def _verify_message(self, message):
        args_encoded = ''
        for arg in sorted(message.command_args.keys()):
            args_encoded += arg + ':' + message.command_args[arg] + ':'

        text = message.from_.split('/')[0] + '::' + \
               message.to.split('/')[0] + '::' + \
               message.command + '::' + \
               args_encoded

        return self._rsa_verify(text, message.signature, message.command, message.from_)

    def _rsa_verify(self, text, signature, command, sender):
        def _emsa_pkcs1_v1_5_encode(M, emLen):
            SHA1DER = '\x30\x21\x30\x09\x06\x05\x2b\x0e\x03\x02\x1a\x05\x00\x04\x14'
            SHA1DERLEN = len(SHA1DER) + 0x14

            H = SHA.new(M).digest()
            T = SHA1DER + H
            if emLen < (SHA1DERLEN + 11):
                log.error('[RSA CHECK: Error] intended encoded message length too short (%s)' % emLen)
                return
            ps = '\xff' * (emLen - SHA1DERLEN - 3)
            if len(ps) < 8:
                log.error('[RSA CHECK: Error] ps length too short')
                return
            return '\x00\x01' + ps + '\x00' + T

        signature = base64.b64decode(signature)
        em = _emsa_pkcs1_v1_5_encode(text, len(signature))

        if em:
            signature = number.bytes_to_long(signature)
            if self.public_key.verify(em, (signature,)):
                log.info("[RSA CHECK: OK] command: %s - from: %s" % (command, sender))
                return True

        log.error("[RSA CHECK: Error] %s - from: %s" % (command, sender))

        del text, signature, command, sender
        del signature, em

        return False
