package br.com.linket.blabla

import io.flutter.embedding.android.FlutterFragmentActivity

// FlutterFragmentActivity (nao FlutterActivity): exigencia do local_auth no
// Android — biometria precisa de uma FragmentActivity pra exibir o prompt.
class MainActivity : FlutterFragmentActivity()
