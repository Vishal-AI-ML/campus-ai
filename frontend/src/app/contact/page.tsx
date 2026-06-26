/**
 * Campus AI - public Contact / demo-request page.
 *
 * Place this file at: src/app/contact/page.tsx
 *
 * Server component (SEO) wrapping the client <ContactForm/>.
 */

import type { Metadata } from "next"
import MarketingShell from "@/components/MarketingShell"
import ContactForm from "@/components/ContactForm"

export const metadata: Metadata = {
	title: "Contact — Campus AI",
	description:
		"Request a demo or talk to our team about bringing Campus AI to your institute.",
}

export default function ContactPage() {
	return (
		<MarketingShell>
			<section className="mx-auto max-w-4xl px-6 py-20">
				<div className="grid gap-10 md:grid-cols-2">
					<div>
						<h1 className="text-4xl font-bold sm:text-5xl">Let's talk</h1>
						<p className="mt-4 text-lg text-slate-300">
							Want to see Campus AI on your campus? Tell us a little about your
							institute and we'll set up a walkthrough.
						</p>
						<ul className="mt-8 space-y-3 text-sm text-slate-300">
							<li className="flex gap-2">
								<span className="text-indigo-300">→</span>
								Personalized demo with seeded data
							</li>
							<li className="flex gap-2">
								<span className="text-indigo-300">→</span>
								Rollout & migration guidance
							</li>
							<li className="flex gap-2">
								<span className="text-indigo-300">→</span>
								Pricing tailored to your size
							</li>
						</ul>
					</div>
					<ContactForm />
				</div>
			</section>
		</MarketingShell>
	)
}
